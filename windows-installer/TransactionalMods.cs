using System.Security;
using System.Text.Json;

namespace TechQuestInstaller;

internal sealed class PackState
{
    public string ReleaseTag { get; set; } = "";
    public List<ManagedMod> Mods { get; set; } = new();
}

internal sealed class RollbackSnapshot
{
    public string CurrentTag { get; set; } = "";
    public string BackupId { get; set; } = "";
    public PackState Previous { get; set; } = new();
}

internal sealed class PendingTransaction
{
    public string BackupId { get; set; } = "";
    public PackState Previous { get; set; } = new();
    public PackState Desired { get; set; } = new();
    public RollbackSnapshot? PreviousRollback { get; set; }
}

// Only TechQuest-managed mod JARs are in the transaction. Never touch the
// user's saves, screenshots, options, config, resource packs, accounts or launcher.
internal static class TransactionalMods
{
    private static readonly JsonSerializerOptions JsonOptions = new() { WriteIndented = true };
    private static readonly StringComparer NameComparer = StringComparer.OrdinalIgnoreCase;

    private static bool SafeName(string value) =>
        !string.IsNullOrEmpty(value) && value.Length <= 180 &&
        value == Path.GetFileName(value) && value.IndexOfAny(Path.GetInvalidFileNameChars()) < 0 &&
        !value.Contains("..", StringComparison.Ordinal) &&
        !value.Contains('/') && !value.Contains('\\') &&
        value.EndsWith(".jar", StringComparison.OrdinalIgnoreCase);

    private static bool IsHash(string s) =>
        s != null && s.Length == 128 && s.All(Uri.IsHexDigit);

    private static string CanonicalRoot(string path)
    {
        if (string.IsNullOrWhiteSpace(path)) throw new ArgumentException("Choose a TechQuest installation folder.");
        string root = Path.GetFullPath(path);
        if (!Directory.Exists(root)) throw new DirectoryNotFoundException("TechQuest installation not found");
        CheckDirectory(root);
        return root;
    }

    private static void CheckDirectory(string path)
    {
        if (Directory.Exists(path) && (File.GetAttributes(path) & FileAttributes.ReparsePoint) != 0)
            throw new SecurityException("Refusing a directory junction/symlink: " + path);
    }

    private static string StateDirectory(string root)
    {
        CheckDirectory(root);
        string state = Path.Combine(root, ".techquest");
        CheckDirectory(state);
        Directory.CreateDirectory(state);
        CheckDirectory(state);
        CheckDirectory(Path.Combine(root, "mods"));
        return state;
    }

    private static string ManagedPath(string mods, ManagedMod file)
    {
        if (!SafeName(file.Name) || !IsHash(file.Sha512) || file.Size is <= 0 or > 536870912)
            throw new SecurityException("Invalid installed mod record.");
        return Path.Combine(mods, file.Name);
    }

    private static void Validate(PackState state)
    {
        if (state.Mods is null || state.Mods.Count > 1000 ||
            state.ReleaseTag.Length > 100)
            throw new SecurityException("Invalid local installation metadata");
        var seen = new HashSet<string>(NameComparer);
        foreach (var item in state.Mods)
        {
            ManagedPath("mods", item);
            if (!seen.Add(item.Name)) throw new SecurityException("Duplicate managed mod entry");
        }
    }

    private static T ReadJson<T>(string path) where T : class
    {
        if ((File.GetAttributes(path) & FileAttributes.ReparsePoint) != 0)
            throw new SecurityException("Unsafe installer state file");
        if (new FileInfo(path).Length > 512 * 1024)
            throw new SecurityException("Installer state is too large");
        return JsonSerializer.Deserialize<T>(File.ReadAllBytes(path))
            ?? throw new InvalidDataException("Invalid installer metadata");
    }

    private static void WriteAtomic<T>(string path, T data)
    {
        if (File.Exists(path) && (File.GetAttributes(path) & FileAttributes.ReparsePoint) != 0)
            throw new SecurityException("Unsafe installer state path");
        string temp = path + "." + Guid.NewGuid().ToString("N") + ".tmp";
        try
        {
            File.WriteAllBytes(temp, JsonSerializer.SerializeToUtf8Bytes(data, JsonOptions));
            File.Move(temp, path, overwrite: true);
        }
        finally { if (File.Exists(temp)) File.Delete(temp); }
    }

    internal static PackState? GetInstalled(string path)
    {
        if (!Directory.Exists(path)) return null;
        string root = CanonicalRoot(path);
        string dir = Path.Combine(root, ".techquest");
        if (!Directory.Exists(dir)) return null;
        CheckDirectory(dir);
        string stateFile = Path.Combine(dir, "state.json");
        if (!File.Exists(stateFile)) return null;
        var state = ReadJson<PackState>(stateFile);
        Validate(state);
        return state;
    }

    // Called after first successful embedded-pack install; makes a later
    // upgrade possible without ever guessing which user mods are safe to remove.
    internal static void RecordInitialInstallation(string root, Stream embeddedPack)
    {
        root = CanonicalRoot(root);
        string stateDir = StateDirectory(root);
        string stateFile = Path.Combine(stateDir, "state.json");
        if (File.Exists(stateFile))
            throw new IOException("This TechQuest profile is already managed.");
        var pack = ReleaseUpdates.ParsePack(embeddedPack);
        string mods = Path.Combine(root, "mods");
        foreach (var file in pack.Mods)
            ReleaseUpdates.VerifyFile(Path.Combine(mods, file.Identity.Name), file.Identity, file.Sha1);
        foreach (var file in pack.BundledMods)
            ReleaseUpdates.VerifyFile(Path.Combine(mods, file.Identity.Name), file.Identity);
        var initial = new PackState
        {
            ReleaseTag = "embedded-" + pack.VersionId,
            Mods = pack.Mods.Select(x => x.Identity)
                .Concat(pack.BundledMods.Select(x => x.Identity)).ToList()
        };
        Validate(initial);
        WriteAtomic(stateFile, initial);
    }

    private static FileStream Lock(string dir) =>
        new(Path.Combine(dir, "updater.lock"), FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None);

    internal static void RecoverPending(string root)
    {
        root = CanonicalRoot(root);
        string dir = StateDirectory(root);
        using var guard = Lock(dir);
        RecoverLocked(root, dir);
    }

    private static void RecoverLocked(string root, string stateDir)
    {
        string journalFile = Path.Combine(stateDir, "transaction.json");
        if (!File.Exists(journalFile)) return;
        var journal = ReadJson<PendingTransaction>(journalFile);
        Validate(journal.Previous);
        Validate(journal.Desired);
        string backup = BackupPath(stateDir, journal.BackupId);
        string mods = Path.Combine(root, "mods");
        var oldMap = journal.Previous.Mods.ToDictionary(x => x.Name, NameComparer);
        // Preflight all backups before deleting anything. Recovery is repeatable.
        foreach (var old in journal.Previous.Mods)
        {
            bool changed = !journal.Desired.Mods.Any(x =>
                NameComparer.Equals(x.Name, old.Name) && x.Sha512 == old.Sha512);
            if (!changed) continue;
            ReleaseUpdates.VerifyFile(Path.Combine(backup, old.Name), old);
        }
        foreach (var next in journal.Desired.Mods)
        {
            if (oldMap.TryGetValue(next.Name, out var old) && old.Sha512 == next.Sha512)
                continue;
            string dest = Path.Combine(mods, next.Name);
            if (File.Exists(dest))
            {
                if ((File.GetAttributes(dest) & FileAttributes.ReparsePoint) != 0)
                    throw new SecurityException("Unsafe recovery destination");
                File.Delete(dest);
            }
        }
        foreach (var old in journal.Previous.Mods)
        {
            bool changed = !journal.Desired.Mods.Any(x =>
                NameComparer.Equals(x.Name, old.Name) && x.Sha512 == old.Sha512);
            if (changed) File.Copy(Path.Combine(backup, old.Name), Path.Combine(mods, old.Name), true);
        }
        WriteAtomic(Path.Combine(stateDir, "state.json"), journal.Previous);
        string oldRollback = Path.Combine(stateDir, "rollback.json");
        if (journal.PreviousRollback is null)
        {
            if (File.Exists(oldRollback)) File.Delete(oldRollback);
        }
        else WriteAtomic(oldRollback, journal.PreviousRollback);
        File.Delete(journalFile);
    }

    private static string BackupPath(string dir, string id)
    {
        if (id.Length != 39 || !id.StartsWith("backup-", StringComparison.Ordinal) ||
            !id["backup-".Length..].All(Uri.IsHexDigit))
            throw new SecurityException("Unsafe backup identity");
        string backups = Path.Combine(dir, "backups");
        CheckDirectory(backups);
        string path = Path.Combine(backups, id);
        CheckDirectory(path);
        return path;
    }

    // Test-only adapter: no network needed to exercise transactional guarantees.
    internal static Task<int> ApplyForTestsAsync(
        string root, PackState desired,
        Func<ManagedMod, string, CancellationToken, Task> stage,
        CancellationToken cancellation) =>
        ApplyAsync(root, desired, stage, null, cancellation);

    internal static async Task<int> UpdateAsync(
        string root, TrustedRelease release, byte[] packBytes,
        IProgress<string>? progress, CancellationToken cancellation)
    {
        using var stream = new MemoryStream(packBytes, writable: false);
        var pack = ReleaseUpdates.ParsePack(stream);
        if (pack.VersionId != release.VersionId)
            throw new SecurityException("Signed version does not match the pack index");
        var sources = pack.Mods.ToDictionary(x => x.Identity.Name, NameComparer);
        var firstParty = pack.BundledMods.ToDictionary(x => x.Identity.Name, NameComparer);
        var desired = pack.Mods.Select(x => x.Identity)
            .Concat(pack.BundledMods.Select(x => x.Identity)).ToList();
        return await ApplyAsync(root,
            new PackState { ReleaseTag = release.Tag, Mods = desired },
            async (item, dest, token) =>
            {
                if (firstParty.TryGetValue(item.Name, out var embedded))
                {
                    token.ThrowIfCancellationRequested();
                    await File.WriteAllBytesAsync(dest, embedded.Bytes, token);
                }
                else
                {
                    await ReleaseUpdates.DownloadCheckedAsync(sources[item.Name].Url,
                        dest, item, sources[item.Name].Sha1, token);
                }
            }, progress, cancellation);
    }

    internal static async Task<int> RollbackAsync(
        string root, IProgress<string>? progress, CancellationToken cancellation)
    {
        root = CanonicalRoot(root);
        string dir = StateDirectory(root);
        // Read metadata now; ApplyAsync rechecks everything under the exclusive lock.
        var rollbackFile = Path.Combine(dir, "rollback.json");
        if (!File.Exists(rollbackFile)) throw new FileNotFoundException("There is no earlier TechQuest version to restore");
        var snapshot = ReadJson<RollbackSnapshot>(rollbackFile);
        Validate(snapshot.Previous);
        string backup = BackupPath(dir, snapshot.BackupId);
        string currentTag = GetInstalled(root)?.ReleaseTag ?? "";
        if (currentTag != snapshot.CurrentTag)
            throw new SecurityException("Rollback snapshot does not match the current installation");
        return await ApplyAsync(root, snapshot.Previous,
            (item, dest, token) =>
            {
                token.ThrowIfCancellationRequested();
                string source = Path.Combine(backup, item.Name);
                ReleaseUpdates.VerifyFile(source, item);
                File.Copy(source, dest);
                return Task.CompletedTask;
            }, progress, cancellation);
    }

    private static async Task<int> ApplyAsync(
        string root, PackState desired,
        Func<ManagedMod, string, CancellationToken, Task> stageMissing,
        IProgress<string>? progress, CancellationToken cancellation)
    {
        root = CanonicalRoot(root);
        string stateDir = StateDirectory(root);
        string mods = Path.Combine(root, "mods");
        if (!Directory.Exists(mods)) throw new DirectoryNotFoundException("Managed mods folder not found");
        Validate(desired);
        using var guard = Lock(stateDir);
        RecoverLocked(root, stateDir);
        string stateFile = Path.Combine(stateDir, "state.json");
        if (!File.Exists(stateFile))
            throw new SecurityException("Unknown profile. Reinstall with the current TechQuest installer first.");
        var current = ReadJson<PackState>(stateFile);
        Validate(current);
        var oldMap = current.Mods.ToDictionary(x => x.Name, NameComparer);
        foreach (var old in current.Mods)
            ReleaseUpdates.VerifyFile(ManagedPath(mods, old), old);
        foreach (var mod in desired.Mods)
            if (!oldMap.ContainsKey(mod.Name) && File.Exists(Path.Combine(mods, mod.Name)))
                throw new SecurityException("Refusing to overwrite user-owned mod: " + mod.Name);

        var newMap = desired.Mods.ToDictionary(x => x.Name, NameComparer);
        var changing = desired.Mods.Where(mod =>
            !oldMap.TryGetValue(mod.Name, out var old) ||
            !string.Equals(old.Sha512, mod.Sha512, StringComparison.OrdinalIgnoreCase)).ToList();
        var retiring = current.Mods.Where(old =>
            !newMap.TryGetValue(old.Name, out var next) ||
            !string.Equals(old.Sha512, next.Sha512, StringComparison.OrdinalIgnoreCase)).ToList();

        if (changing.Count == 0 && retiring.Count == 0 && current.ReleaseTag == desired.ReleaseTag)
            return 0;

        string id = Guid.NewGuid().ToString("N");
        string stage = Path.Combine(stateDir, "pending-" + id);
        string backupId = "backup-" + id;
        string backup = BackupPath(stateDir, backupId);
        Directory.CreateDirectory(stage);
        bool journalWritten = false;
        try
        {
            for (int index = 0; index < changing.Count; index++)
            {
                cancellation.ThrowIfCancellationRequested();
                var item = changing[index];
                progress?.Report($"Проверка/загрузка {index + 1}/{changing.Count}: {item.Name}");
                string downloaded = Path.Combine(stage, item.Name);
                await stageMissing(item, downloaded, cancellation);
                ReleaseUpdates.VerifyFile(downloaded, item);
            }
            cancellation.ThrowIfCancellationRequested();
            Directory.CreateDirectory(backup);
            foreach (var old in retiring)
            {
                string copy = Path.Combine(backup, old.Name);
                File.Copy(Path.Combine(mods, old.Name), copy);
                ReleaseUpdates.VerifyFile(copy, old);
            }
            // Durable journal is written only after all backups are verified.
            WriteAtomic(Path.Combine(stateDir, "transaction.json"), new PendingTransaction
            {
                Previous = current, Desired = desired, BackupId = backupId,
                PreviousRollback = File.Exists(Path.Combine(stateDir, "rollback.json"))
                    ? ReadJson<RollbackSnapshot>(Path.Combine(stateDir, "rollback.json")) : null
            });
            journalWritten = true;
            foreach (var old in retiring)
                File.Delete(Path.Combine(mods, old.Name));
            foreach (var next in changing)
                File.Move(Path.Combine(stage, next.Name), Path.Combine(mods, next.Name), false);
            foreach (var mod in desired.Mods)
                ReleaseUpdates.VerifyFile(Path.Combine(mods, mod.Name), mod);
            WriteAtomic(stateFile, desired);
            WriteAtomic(Path.Combine(stateDir, "rollback.json"), new RollbackSnapshot
            {
                CurrentTag = desired.ReleaseTag, Previous = current, BackupId = backupId
            });
            File.Delete(Path.Combine(stateDir, "transaction.json"));
            journalWritten = false;
            progress?.Report("Обновление успешно установлено. Можно запустить официальный Minecraft Launcher.");
            return changing.Count;
        }
        catch
        {
            if (journalWritten)
            {
                // If recovery also fails, leave the journal and backup intact for the next launch.
                RecoverLocked(root, stateDir);
            }
            throw;
        }
        finally
        {
            if (Directory.Exists(stage)) Directory.Delete(stage, recursive: true);
        }
    }
}
