using System.Security;

namespace TechQuestInstaller;

// Migration from a pre-updater TechQuest install is deliberately narrow:
// allow ONLY missing exact files from the EXE's embedded pinned pack.
// Never try to "convert" a different modpack by deleting/replacing its files.
internal sealed record LegacyProfileInspection(
    string Version, int Verified, int Missing, int Unknown,
    IReadOnlyList<string> MissingNames);

internal static partial class TransactionalMods
{
    internal static LegacyProfileInspection InspectLegacy(string root, Stream packStream)
    {
        var pack = ReleaseUpdates.ParsePack(packStream);
        return InspectLegacyPack(root, pack);
    }

    private static LegacyProfileInspection InspectLegacyPack(string root, ReleasePack pack)
    {
        root = CanonicalRoot(root);
        string mods = Path.Combine(root, "mods");
        if (!Directory.Exists(mods)) throw new DirectoryNotFoundException("No mods directory in the selected profile");
        CheckDirectory(mods);
        string stateDir = Path.Combine(root, ".techquest");
        CheckDirectory(stateDir);
        if (File.Exists(Path.Combine(stateDir, "state.json")) ||
            File.Exists(Path.Combine(stateDir, "transaction.json")))
            throw new SecurityException("Managed or interrupted profile cannot be imported as legacy.");

        var expected = pack.Mods.Select(x => x.Identity)
            .Concat(pack.BundledMods.Select(x => x.Identity)).ToList();
        if (expected.Count is < 5 or > 1000)
            throw new InvalidDataException("Invalid pinned TechQuest pack");
        var names = new HashSet<string>(expected.Select(x => x.Name), NameComparer);
        if (names.Count != expected.Count) throw new SecurityException("Duplicate TechQuest file name");
        var missing = new List<string>();
        int verified = 0;
        foreach (var mod in expected)
        {
            string path = ManagedPath(mods, mod);
            if (!File.Exists(path))
            {
                // Even broken symlinks must not be treated as absent files.
                if (Path.Exists(path))
                    throw new SecurityException("Unexpected filesystem entry: " + mod.Name);
                missing.Add(mod.Name);
                continue;
            }
            ReleaseUpdates.VerifyFile(path, mod);
            verified++;
        }
        int threshold = Math.Max(3, (int)Math.Ceiling(expected.Count * 0.75));
        if (verified < threshold)
            throw new InvalidDataException(
                $"This is not the exact TechQuest {pack.VersionId} installation " +
                $"({verified}/{expected.Count} verified files, need at least {threshold}). " +
                "Choose the matching signed release, or a separate empty folder.");
        int unknown = 0;
        foreach (var file in Directory.EnumerateFiles(mods, "*.jar", SearchOption.TopDirectoryOnly))
            if (!names.Contains(Path.GetFileName(file))) unknown++;
        return new LegacyProfileInspection(pack.VersionId, verified, missing.Count, unknown, missing);
    }

    internal static async Task<LegacyProfileInspection> AdoptLegacyWithEmbeddedAsync(
        string root, Stream embedded, IProgress<string>? progress, CancellationToken cancellation)
    {
        var pack = ReleaseUpdates.ParsePack(embedded);
        var downloads = pack.Mods.ToDictionary(x => x.Identity.Name, NameComparer);
        var internalMods = pack.BundledMods.ToDictionary(x => x.Identity.Name, NameComparer);
        return await AdoptLegacyCoreAsync(root, pack, async (mod, path, token) =>
        {
            if (internalMods.TryGetValue(mod.Name, out var asset))
                await File.WriteAllBytesAsync(path, asset.Bytes, token);
            else
            {
                var source = downloads[mod.Name];
                await ReleaseUpdates.DownloadCheckedAsync(source.Url, path,
                    mod, source.Sha1, token);
            }
        }, progress, cancellation);
    }

    internal static Task<LegacyProfileInspection> AdoptLegacyForTestsAsync(
        string root, ReleasePack pack,
        Func<ManagedMod, string, CancellationToken, Task> download,
        CancellationToken cancellation) =>
        AdoptLegacyCoreAsync(root, pack, download, null, cancellation);

    private static async Task<LegacyProfileInspection> AdoptLegacyCoreAsync(
        string root, ReleasePack pack,
        Func<ManagedMod, string, CancellationToken, Task> download,
        IProgress<string>? progress, CancellationToken cancellation)
    {
        // Inspect before writing to disk; no download or game-folder changes if any
        // existing expected JAR is modified, or the profile is from another version.
        var inspection = InspectLegacyPack(root, pack);
        root = CanonicalRoot(root);
        string stateDir = StateDirectory(root);
        string mods = Path.Combine(root, "mods");
        using var guard = Lock(stateDir);
        inspection = InspectLegacyPack(root, pack);
        var all = pack.Mods.Select(x => x.Identity)
            .Concat(pack.BundledMods.Select(x => x.Identity)).ToList();
        var lookup = all.ToDictionary(x => x.Name, NameComparer);
        string stage = Path.Combine(stateDir, "legacy-repair-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(stage);
        try
        {
            for (int i = 0; i < inspection.MissingNames.Count; i++)
            {
                cancellation.ThrowIfCancellationRequested();
                string name = inspection.MissingNames[i];
                var expected = lookup[name];
                string stagedFile = Path.Combine(stage, name);
                progress?.Report($"Загрузка отсутствующего мода {i + 1}/{inspection.Missing}: {name}");
                await download(expected, stagedFile, cancellation);
                ReleaseUpdates.VerifyFile(stagedFile, expected);
            }

            // Recheck all existing files after downloads, before any installation;
            // an unexpected file is never overwritten.
            cancellation.ThrowIfCancellationRequested();
            var confirm = InspectLegacyPack(root, pack);
            if (confirm.Verified != inspection.Verified ||
                !confirm.MissingNames.SequenceEqual(inspection.MissingNames, NameComparer))
                throw new IOException("The profile changed during download. No files were replaced.");

            foreach (string name in inspection.MissingNames)
            {
                // Atomic on the same volume. File.Move without overwrite prevents
                // replacing user-owned data on a concurrent filesystem change.
                File.Move(Path.Combine(stage, name), Path.Combine(mods, name), false);
            }
            foreach (var item in all)
                ReleaseUpdates.VerifyFile(Path.Combine(mods, item.Name), item);

            var statePath = Path.Combine(stateDir, "state.json");
            if (File.Exists(statePath)) throw new IOException("Profile became managed during import");
            WriteAtomic(statePath, new PackState
            {
                ReleaseTag = "embedded-" + pack.VersionId,
                Mods = all
            });
            progress?.Report(inspection.Missing == 0
                ? "Существующая сборка проверена и подключена."
                : $"Установлено недостающих модов: {inspection.Missing}. Сборка подключена.");
            return inspection;
        }
        finally
        {
            if (Directory.Exists(stage)) Directory.Delete(stage, true);
        }
    }
}
