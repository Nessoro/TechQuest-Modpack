using System.Diagnostics;
using System.IO.Compression;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace TechQuestInstaller;

internal static class Program
{
    [STAThread]
    private static void Main(string[] args)
    {
        if (args.Contains("--self-test", StringComparer.OrdinalIgnoreCase))
        {
            Environment.ExitCode = InstallerForm.VerifyEmbeddedPacks();
            return;
        }
        ApplicationConfiguration.Initialize();
        Application.Run(new InstallerForm());
    }
}

internal sealed partial class InstallerForm : Form
{
    private const string NeoForgeVersion = "21.1.264";
    private static readonly HttpClient Client = new() { Timeout = TimeSpan.FromMinutes(5) };

    private readonly TextBox location = new() { Width = 540 };
    private readonly Button browse = new() { Text = "Обзор…", Width = 110 };
    private readonly Button install = new() { Text = "1. Установить моды", Width = 205, Height = 45 };
    private readonly Button neoforge = new() { Text = "2. Установить NeoForge", Width = 205, Height = 45 };
    private readonly Button openFolder = new() { Text = "Открыть папку", Width = 150, Height = 37 };
    private readonly Button help = new() { Text = "Инструкция", Width = 130, Height = 37 };
    private readonly Button importAmw = new() { Text = "3. Добавить AMW", Width = 205, Height = 37 };
    private readonly Button cancel = new() { Text = "Отмена", Width = 100, Height = 37, Enabled = false };
    private readonly Button checkUpdates = new() { Text = "Проверить GitHub", Width = 225, Height = 45 };
    private readonly Button applyUpdate = new() { Text = "Обновить сборку", Width = 205, Height = 39, Enabled = false };
    private readonly Button rollback = new() { Text = "Откатить обновление", Width = 205, Height = 39 };
    private readonly Button downloadExe = new() { Text = "Новый EXE", Width = 205, Height = 39, Enabled = false };
    private readonly CheckBox previewUpdates = new() { Text = "Включая тестовые релизы", Checked = true, AutoSize = true };
    private TrustedRelease? availableRelease;
    private bool updateAvailable;
    private readonly ProgressBar progress = new() { Width = 695, Height = 19 };
    private readonly Label status = new() { Text = "Готово к установке. Minecraft Launcher и Java 21 устанавливаются отдельно.", AutoSize = false, Width = 710, Height = 45 };
    private CancellationTokenSource? cancellation;
    private readonly string baseDir = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "TechQuest");
    private string? installedGameDir;

    internal InstallerForm()
    {
        BuildLauncherLayout();

        location.Text = Path.Combine(baseDir, "TechQuest_0.3.3_Alpha");
        browse.Click += (_, _) =>
        {
            using var dialog = new FolderBrowserDialog
            {
                Description = "Выберите папку TechQuest (новую или ранее установленную)",
                SelectedPath = Directory.Exists(location.Text) ? location.Text : baseDir,
                ShowNewFolderButton = true
            };
            if (dialog.ShowDialog(this) == DialogResult.OK) location.Text = dialog.SelectedPath;
        };
        location.TextChanged += (_, _) => RefreshProfileStatus();

        install.Click += async (_, _) => await PrimaryActionAsync();
        verifyIntegrity.Click += async (_, _) => await RepairMissingAsync();
        playOfficial.Click += (_, _) => LaunchMinecraftOfficially();
        neoforge.Click += async (_, _) => await NeoForgeAsync();
        openFolder.Click += (_, _) =>
        {
            var path = installedGameDir ?? location.Text;
            if (Directory.Exists(path))
                Process.Start(new ProcessStartInfo(path) { UseShellExecute = true });
        };
        cancel.Click += (_, _) => cancellation?.Cancel();
        help.Click += (_, _) => ShowInstructions();
        importAmw.Click += (_, _) => ImportAcceleratedMcWarfare();
        checkUpdates.Click += async (_, _) => await CheckForUpdatesAsync();
        applyUpdate.Click += async (_, _) => await ApplyUpdateAsync();
        rollback.Click += async (_, _) => await RollbackAsync();
        downloadExe.Click += async (_, _) => await DownloadNewInstallerAsync();
        previewUpdates.CheckedChanged += async (_, _) => await CheckForUpdatesAsync();
        Shown += async (_, _) =>
        {
            RefreshProfileStatus();
            await CheckForUpdatesAsync();
        };
        RefreshProfileStatus();
    }

    private void SetBusy(bool busy, bool cancellable)
    {
        install.Enabled = !busy;
        neoforge.Enabled = !busy;
        importAmw.Enabled = !busy;
        playOfficial.Enabled = !busy && currentProfile == ProfileMode.Managed;
        verifyIntegrity.Enabled = !busy && currentProfile == ProfileMode.Managed;
        browse.Enabled = !busy;
        checkUpdates.Enabled = !busy;
        applyUpdate.Enabled = !busy && availableRelease != null && updateAvailable;
        rollback.Enabled = !busy && currentProfile == ProfileMode.Managed &&
            File.Exists(Path.Combine(location.Text, ".techquest", "rollback.json"));
        downloadExe.Enabled = !busy && availableRelease != null;
        previewUpdates.Enabled = !busy;
        location.ReadOnly = busy;
        cancel.Enabled = busy && cancellable;
        UseWaitCursor = busy;
        if (!busy) RefreshProfileStatus();
    }

    private void ShowInstructions()
    {
        MessageBox.Show(this,
            "1. Выберите новую или уже установленную папку TechQuest; Python и консоль не нужны.\n" +
            "   Требуются лицензионная Minecraft Java Edition, вход в официальный Launcher Microsoft.\n" +
            "   TechQuest никогда не запрашивает и не хранит пароль Microsoft, токены или cookies.\n" +
            "2. Для уже установленной TechQuest нажмите «Проверить TechQuest».\n" +
            "3. Установите Java 21, если её нет на компьютере.\n" +
            "4. Нажмите «Установить NeoForge», в его окне выберите Install client.\n" +
            "5. Откройте официальный Minecraft Launcher → Установки → NeoForge 21.1.264 → Изменить.\n" +
            "6. В «Папка игры / Game Directory» укажите выбранный здесь путь.\n" +
            "7. Запускайте профиль NeoForge, НЕ обычную ванильную Minecraft 1.21.1.\n" +
            "8. AMW (необязательно): скачайте официальный JAR с CurseForge, затем нажмите «Добавить AMW».\n" +
            "   Для сервера положите тот же JAR в mods и проверьте совместимость с Incoming.\n" +
            "Оптимизированный профиль: графика Fast, 4–6 чанков, без шейдеров,\n" +
            "6 ГБ RAM при наличии 16 ГБ системной памяти.\n\n" +
            "В игре: Xaero Minimap/World Map, здоровье мобов Health Indicator TXF (HP цифрами),\n" +
            "книга «Путеводитель TechQuest» через Patchouli (в творческом режиме).\n" +
            "В режиме выживания руководство выдаётся при первом входе в мир.\n" +
            "Project MMO и TechQuest RPG Core исключены из текущего профиля.\n\n" +
            "Сервер общий; все игровые механики сохранены. Тестируйте новый мир.",
            "Как запустить TechQuest", MessageBoxButtons.OK, MessageBoxIcon.Information);
    }

    private static Stream GetEmbeddedPack()
    {
        const string name = "TechQuest.Optimized.mrpack";
        return Assembly.GetExecutingAssembly().GetManifestResourceStream(name)
            ?? throw new InvalidDataException("Сборка " + name + " не встроена в установщик.");
    }

    internal static int VerifyEmbeddedPacks()
    {
        try
        {
            using var resource = GetEmbeddedPack();
            var mods = LoadManifest(resource);
            var fileNames = mods.Select(x => x.Name.ToLowerInvariant()).ToArray();
            string[] core = { "industrial-craft-2-nostalgia", "buildcraft", "create-", "mekanism", "incoming-3.10.4" };
            string[] optimization = { "sodium-", "immediatelyfast", "moreculling", "badoptimizations", "dynamic-fps" };
            if (core.Any(id => !fileNames.Any(n => n.Contains(id)))) return 2;
            if (optimization.Any(id => !fileNames.Any(n => n.Contains(id)))) return 3;
            if (fileNames.Any(n => n.StartsWith("iris-"))) return 4;
            var normalized = fileNames.Select(n =>
                n.Replace("-", "").Replace("_", "").Replace(" ", "")).ToArray();
            if (!normalized.Any(n => n.Contains("xaero") && n.Contains("minimap")) ||
                !normalized.Any(n => n.Contains("xaero") && n.Contains("worldmap")) ||
                !normalized.Any(n => n.Contains("healthindicator")) ||
                !normalized.Any(n => n.Contains("patchouli")))
                return 6;
            using var zipStream = GetEmbeddedPack();
            using var archive = new ZipArchive(zipStream, ZipArchiveMode.Read);
            if (archive.GetEntry("overrides/patchouli_books/techquest_guide/book.json") is null ||
                archive.GetEntry("overrides/config/openloader/packs/techquest_starter_guide.zip") is null ||
                archive.GetEntry("overrides/config/openloader/packs/techquest_micropatch_033.zip") is null ||
                archive.GetEntry("overrides/defaultconfigs/modern_industrialization-server.toml") is null ||
                 fileNames.Any(n => n.StartsWith("pmmo-", StringComparison.OrdinalIgnoreCase)) ||
                 archive.GetEntry("overrides/mods/techquest-compat-1.0.0.jar") is null ||
                 archive.Entries.Any(e =>
                     e.FullName.StartsWith("overrides/mods/techquest-rpg-core", StringComparison.OrdinalIgnoreCase) ||
                     e.FullName.StartsWith("overrides/mods/pmmo-", StringComparison.OrdinalIgnoreCase) ||
                     e.FullName.StartsWith("overrides/mods/project-mmo", StringComparison.OrdinalIgnoreCase)))
                return 7;
            string probe = Path.Combine(Path.GetTempPath(), "TechQuest-self-test-" + Guid.NewGuid().ToString("N"));
            try
            {
                InstallGuideOverrides(probe);
                string miDefault = File.ReadAllText(Path.Combine(probe, "defaultconfigs",
                    "modern_industrialization-server.toml"));
                if (!miDefault.Contains("spawnWithGuideBook = true") ||
                    !miDefault.Contains("respawnWithGuideBook = false")) return 27;
                string miWorld = Path.Combine(probe, "saves", "mi-world", "serverconfig");
                Directory.CreateDirectory(miWorld);
                string miPath = Path.Combine(miWorld, "modern_industrialization-server.toml");
                const string miOriginal = "forgeEnergyPerEu = 17\nspawnWithGuideBook = true\nrespawnWithGuideBook = true\n[recipes]\ncompostableToPlantOil = false\n";
                File.WriteAllText(miPath, miOriginal);
                InstallGuideOverrides(probe);
                // Never change existing world data from the launcher.
                if (File.ReadAllText(miPath) != miOriginal) return 28;
                InstallGuideOverrides(probe);
                if (File.ReadAllText(miPath) != miOriginal ||
                    File.Exists(miPath + ".techquest-original.bak")) return 29;
                string options = File.ReadAllText(Path.Combine(probe, "options.txt"));
                if (!options.Split('\n').Contains("graphicsMode:0") ||
                    !options.Split('\n').Contains("maxFps:60")) return 8;
                File.WriteAllText(Path.Combine(probe, "options.txt"), "existing-player-settings");
                InstallGuideOverrides(probe);
                if (File.ReadAllText(Path.Combine(probe, "options.txt")) != "existing-player-settings") return 9;
                if (fileNames.Any(n => n.StartsWith("betterzoom-")))
                {
                    if (!options.Split('\n').Contains("key_key.betterzoom.zoom:key.keyboard.z") ||
                        !options.Split('\n').Contains("key_gui.xaero_enlarge_map:key.keyboard.f9") ||
                        !options.Split('\n').Contains("key_key.sophisticatedbackpacks.toggle_upgrade_1:key.keyboard.f10")) return 12;
                    string zoomConfig = Path.Combine(probe, "config", "betterzoom-client.toml");
                    if (!File.ReadAllText(zoomConfig).Contains("holdToZoom = true")) return 13;
                    File.WriteAllText(zoomConfig, "existing-player-zoom-settings");
                    InstallGuideOverrides(probe);
                    if (File.ReadAllText(zoomConfig) != "existing-player-zoom-settings") return 14;
                }
                if (fileNames.Any(n => n.StartsWith("physics-mod-")))
                {
                    string configDir = Path.Combine(probe, "config", "physicsmod");
                    string clientConfig = Path.Combine(configDir, "physics_client_config.json");
                    string localServerConfig = Path.Combine(configDir, "physics_server_config.json");
                    using var clientJson = JsonDocument.Parse(File.ReadAllText(clientConfig));
                    using var serverJson = JsonDocument.Parse(File.ReadAllText(localServerConfig));
                    if (clientJson.RootElement.GetProperty("maxPhysicsObjects").GetInt32() != 128 ||
                        clientJson.RootElement.GetProperty("blockPhysicsRange").GetDouble() != 16 ||
                        serverJson.RootElement.GetProperty("collapse").GetBoolean()) return 10;
                    File.WriteAllText(clientConfig, "existing-physics-settings");
                    File.WriteAllText(localServerConfig, "existing-collapse-settings");
                    InstallGuideOverrides(probe);
                    if (File.ReadAllText(clientConfig) != "existing-physics-settings" ||
                        File.ReadAllText(localServerConfig) != "existing-collapse-settings") return 11;
                }
                if (fileNames.Any(n => n.StartsWith("healthindicatortxf-")))
                {
                    string[] presets = { "healthindicatortxf.json5", "jade/plugins.json",
                        "explosionoverhaul/explosionoverhaul-client.toml", "incoming-client.toml" };
                    using var hud = JsonDocument.Parse(File.ReadAllText(Path.Combine(probe, "config", presets[0])));
                    if (hud.RootElement.GetProperty("position").GetString() != "TOP_CENTER" ||
                        !hud.RootElement.GetProperty("showHealth").GetBoolean()) return 17;
                    using var jade = JsonDocument.Parse(File.ReadAllText(Path.Combine(probe, "config", presets[1])));
                    if (jade.RootElement.GetProperty("minecraft").GetProperty("entity_health").GetBoolean()) return 18;
                    foreach (string relative in presets)
                        File.WriteAllText(Path.Combine(probe, "config", relative), "existing-player-settings");
                    InstallGuideOverrides(probe);
                    foreach (string relative in presets)
                        if (File.ReadAllText(Path.Combine(probe, "config", relative)) != "existing-player-settings") return 19;
                }
            }
            finally
            {
                if (Directory.Exists(probe)) Directory.Delete(probe, recursive: true);
            }
            // Transactional upgrade/rollback tests reside in tests/updater.
            Directory.CreateDirectory(probe);
            // Caching is only allowed after checking BOTH file size and SHA;
            // stale or tampered JARs are never reused.
            byte[] sample = Encoding.UTF8.GetBytes("verified-existing-jar");
            string cacheTest = Path.Combine(probe, "cache-test.jar");
            File.WriteAllBytes(cacheTest, sample);
            var sampleMod = new ModFile("cache-test.jar",
                new Uri("https://cdn.modrinth.com/data/example.jar"),
                Convert.ToHexString(SHA512.HashData(sample)), null, sample.Length);
            if (!IsVerifiedLocalJar(sampleMod, cacheTest)) return 24;
            string cacheStage = Path.Combine(probe, "cached-stage");
            Directory.CreateDirectory(cacheStage);
            if (!TryReuseVerifiedJar(sampleMod, probe, Path.Combine(probe, "missing-backup"), cacheStage) ||
                !IsVerifiedLocalJar(sampleMod, Path.Combine(cacheStage, sampleMod.Name))) return 26;
            File.Delete(Path.Combine(cacheStage, sampleMod.Name));
            File.WriteAllBytes(cacheTest, Encoding.UTF8.GetBytes("tampered-existing-jar"));
            if (IsVerifiedLocalJar(sampleMod, cacheTest)) return 25;
            if (TryReuseVerifiedJar(sampleMod, probe, Path.Combine(probe, "missing-backup"), cacheStage)) return 27;
            Directory.Delete(cacheStage, recursive: true);
            File.Delete(cacheTest);
            Directory.Delete(probe, recursive: true);
            return 0;
        }
        catch { return 5; }
    }

    private sealed record ModFile(string Name, Uri Url, string? Sha512, string? Sha1, long Size);

    private static List<ModFile> LoadManifest(Stream packStream)
    {
        using var archive = new ZipArchive(packStream, ZipArchiveMode.Read);
        var entry = archive.GetEntry("modrinth.index.json")
            ?? throw new InvalidDataException("Отсутствует modrinth.index.json");
        using var doc = JsonDocument.Parse(entry.Open());
        var root = doc.RootElement;
        if (root.GetProperty("game").GetString() != "minecraft")
            throw new InvalidDataException("Неподдерживаемый тип пакета.");
        var deps = root.GetProperty("dependencies");
        if (deps.GetProperty("minecraft").GetString() != "1.21.1" ||
            deps.GetProperty("neoforge").GetString() != NeoForgeVersion)
            throw new InvalidDataException("Требуется Minecraft 1.21.1 / NeoForge " + NeoForgeVersion);
        var output = new List<ModFile>();
        var known = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var file in root.GetProperty("files").EnumerateArray())
        {
            if (file.GetProperty("env").TryGetProperty("client", out var side) &&
                side.GetString() == "unsupported")
                continue;
            string path = file.GetProperty("path").GetString() ?? "";
            if (!path.StartsWith("mods/", StringComparison.Ordinal) ||
                path[5..] != Path.GetFileName(path[5..]) ||
                path.Contains('\\') || path.Contains("..", StringComparison.Ordinal) ||
                !path.EndsWith(".jar", StringComparison.OrdinalIgnoreCase))
                throw new InvalidDataException("Недопустимый путь JAR в пакете: " + path);
            var name = path[5..];
            if (name.StartsWith("techquest-rpg-core", StringComparison.OrdinalIgnoreCase) ||
                name.StartsWith("pmmo-", StringComparison.OrdinalIgnoreCase) ||
                name.StartsWith("project-mmo", StringComparison.OrdinalIgnoreCase))
                throw new InvalidDataException("Удалённый мод запрещён в micro3: " + name);
            if (!known.Add(name)) throw new InvalidDataException("Повтор файла: " + name);
            var downloads = file.GetProperty("downloads");
            if (downloads.GetArrayLength() < 1 ||
                !Uri.TryCreate(downloads[0].GetString(), UriKind.Absolute, out var url) ||
                url.Scheme != Uri.UriSchemeHttps ||
                (url.Host != "cdn.modrinth.com" &&
                 url.Host != "raw.githubusercontent.com" &&
                 !(url.Host == "maven.ftb.dev" &&
                   (url.AbsolutePath == "/releases/dev/ftb/mods/ftb-library-neoforge/2101.1.39/ftb-library-neoforge-2101.1.39.jar" ||
                    url.AbsolutePath == "/releases/dev/ftb/mods/ftb-ultimine-neoforge/2101.1.15/ftb-ultimine-neoforge-2101.1.15.jar") &&
                   string.IsNullOrEmpty(url.Query) && string.IsNullOrEmpty(url.Fragment)) &&
                 !(url.Host == "github.com" &&
                   url.AbsolutePath == "/zentixua/incoming/releases/download/v3.10.4/incoming-3.10.4.jar" &&
                   string.IsNullOrEmpty(url.Query) && string.IsNullOrEmpty(url.Fragment))))
                throw new InvalidDataException("Недоверенный URL мода: " + name);
            var hashes = file.GetProperty("hashes");
            string? sha512 = hashes.TryGetProperty("sha512", out var h512) ? h512.GetString() : null;
            string? sha1 = hashes.TryGetProperty("sha1", out var h1) ? h1.GetString() : null;
            if (sha512 is null && sha1 is null)
                throw new InvalidDataException("Нет контрольной суммы для " + name);
            long size = file.TryGetProperty("fileSize", out var sizeValue) ? sizeValue.GetInt64() : 0;
            if (size <= 0 || size > 512L * 1024 * 1024)
                throw new InvalidDataException("Недопустимый размер мода: " + name);
            output.Add(new ModFile(name, url, sha512, sha1, size));
        }
        if (output.Count == 0) throw new InvalidDataException("Моды не найдены.");
        return output;
    }

    private static bool IsVerifiedLocalJar(ModFile file, string path)
    {
        if (!File.Exists(path) || new FileInfo(path).Length != file.Size)
            return false;
        try
        {
            if (file.Sha512 is not null)
            {
                using var sha = SHA512.Create();
                using var stream = File.OpenRead(path);
                if (!sha.ComputeHash(stream).AsSpan().SequenceEqual(Convert.FromHexString(file.Sha512)))
                    return false;
            }
            if (file.Sha1 is not null)
            {
                using var sha = SHA1.Create();
                using var stream = File.OpenRead(path);
                if (!sha.ComputeHash(stream).AsSpan().SequenceEqual(Convert.FromHexString(file.Sha1)))
                    return false;
            }
            return file.Sha512 is not null || file.Sha1 is not null;
        }
        catch (IOException) { return false; }
        catch (UnauthorizedAccessException) { return false; }
    }

    private static bool TryReuseVerifiedJar(ModFile file, string existingMods,
                                             string previousMods, string staging)
    {
        foreach (string folder in new[] { existingMods, previousMods })
        {
            string candidate = Path.Combine(folder, file.Name);
            if (!IsVerifiedLocalJar(file, candidate))
                continue;
            string destination = Path.Combine(staging, file.Name);
            File.Copy(candidate, destination, overwrite: true);
            if (IsVerifiedLocalJar(file, destination))
                return true;
            File.Delete(destination);
        }
        return false;
    }

    private static async Task DownloadCheckedAsync(ModFile file, string destination, CancellationToken token)
    {
        using var response = await Client.GetAsync(file.Url, HttpCompletionOption.ResponseHeadersRead, token);
        response.EnsureSuccessStatusCode();
        await using (var input = await response.Content.ReadAsStreamAsync(token))
        await using (var output = File.Create(destination))
            await input.CopyToAsync(output, token);
        if (!IsVerifiedLocalJar(file, destination))
            throw new InvalidDataException("Размер или SHA не совпадает: " + file.Name);
    }

    // Bound retries for temporary CDN/routing problems; do not alter pinned URLs or hashes.
    private static async Task DownloadWithRetryAsync(ModFile file, string destination, CancellationToken token)
    {
        for (int attempt = 1; attempt <= 3; attempt++)
        {
            token.ThrowIfCancellationRequested();
            try
            {
                await DownloadCheckedAsync(file, destination, token);
                return;
            }
            catch (Exception ex) when (attempt < 3 &&
                  (ex is HttpRequestException || ex is IOException || ex is InvalidDataException))
            {
                if (File.Exists(destination)) File.Delete(destination);
                await Task.Delay(TimeSpan.FromMilliseconds(650 * attempt * attempt), token);
            }
        }
    }

    private static void InstallGuideOverrides(string gameDirectory)
    {
        // The .mrpack is a trusted embedded build artifact. Still restrict every
        // extracted path to a narrow first-party allowlist to avoid ZIP traversal.
        using var stream = GetEmbeddedPack();
        using var zip = new ZipArchive(stream, ZipArchiveMode.Read);
        string safeRoot = Path.GetFullPath(gameDirectory).TrimEnd(Path.DirectorySeparatorChar)
                          + Path.DirectorySeparatorChar;
        foreach (var entry in zip.Entries)
        {
            if (!entry.FullName.StartsWith("overrides/", StringComparison.Ordinal))
                continue;
            string relative = entry.FullName["overrides/".Length..];
            bool allowed =
                relative.StartsWith("patchouli_books/techquest_guide/", StringComparison.Ordinal) ||
                relative == "config/openloader/packs/techquest_starter_guide.zip" ||
                relative == "config/openloader/packs/techquest_micropatch_033.zip" ||
                relative == "mods/techquest-compat-1.0.0.jar" ||
                relative == "TECHQUEST_INGAME_GUIDE.txt" ||
                relative == "options.txt" ||
                relative == "config/physicsmod/physics_client_config.json" ||
                relative == "config/physicsmod/physics_server_config.json" ||
                relative == "config/betterzoom-client.toml" ||
                
                relative == "config/incoming-client.toml" ||
                relative == "config/explosionoverhaul/explosionoverhaul-client.toml" ||
                relative == "config/jade/plugins.json" ||
                relative == "config/healthindicatortxf.json5" ||
                relative == "defaultconfigs/openpartiesandclaims-server.toml" ||
                relative == "defaultconfigs/modern_industrialization-server.toml" ||
                relative == "TECHQUEST_OPTIMIZED.txt" ||
                relative == "TECHQUEST_OPTIONAL_LOCAL_MODS.json";
            if (!allowed || relative.EndsWith("/", StringComparison.Ordinal))
                continue;
            if (relative.Contains("..", StringComparison.Ordinal) ||
                relative.Contains('\\') || Path.IsPathRooted(relative))
                throw new InvalidDataException("Invalid guide override path: " + relative);
            string destination = Path.GetFullPath(Path.Combine(gameDirectory,
                relative.Replace('/', Path.DirectorySeparatorChar)));
            if (!destination.StartsWith(safeRoot, StringComparison.OrdinalIgnoreCase))
                throw new InvalidDataException("Guide override escaped the install folder.");
            Directory.CreateDirectory(Path.GetDirectoryName(destination)!);
            // Protect existing player-created files; install into an empty profile.
            if (File.Exists(destination))
                continue;
            using var source = entry.Open();
            using var output = File.Create(destination);
            source.CopyTo(output);
        }
    }

    private void ImportAcceleratedMcWarfare()
    {
        const string expectedName = "acceleratedMcWarfare-1.0.4..jar";
        const string releaseUrl = "https://www.curseforge.com/minecraft/mc-mods/amw/files/9298161";
        try
        {
            string gameDir = Path.GetFullPath(location.Text);
            string modsDir = Path.Combine(gameDir, "mods");
            if (!Directory.Exists(modsDir) || !Directory.EnumerateFiles(modsDir, "*.jar").Any())
            {
                MessageBox.Show(this, "Сначала установите TechQuest в отдельную папку.",
                    "Установка AMW", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }
            if (!Directory.EnumerateFiles(modsDir, "*.jar").Any(f =>
                    Path.GetFileName(f).Contains("geckolib", StringComparison.OrdinalIgnoreCase)))
            {
                MessageBox.Show(this, "Не найдена обязательная библиотека GeckoLib. Сначала установите полный модпак.",
                    "AMW: не хватает GeckoLib", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }
            using var dialog = new OpenFileDialog
            {
                Title = "Выберите официальный acceleratedMcWarfare-1.0.4..jar из CurseForge",
                Filter = "Minecraft NeoForge мод (*.jar)|*.jar",
                Multiselect = false
            };
            if (dialog.ShowDialog(this) != DialogResult.OK)
                return;
            string source = dialog.FileName;
            if (!string.Equals(Path.GetFileName(source), expectedName, StringComparison.OrdinalIgnoreCase))
                throw new InvalidDataException("Файл должен быть оригинальным " + expectedName);
            var file = new FileInfo(source);
            if (file.Length < 1024 * 1024 || file.Length > 100L * 1024 * 1024)
                throw new InvalidDataException("Размер JAR не соответствует ожидаемым ограничениям.");
            using (var archive = ZipFile.OpenRead(source))
            {
                if (archive.Entries.Count == 0 || archive.Entries.Count > 30000 ||
                    !archive.Entries.Any(e =>
                        e.FullName is "META-INF/neoforge.mods.toml" or "META-INF/mods.toml"))
                    throw new InvalidDataException("Файл не похож на NeoForge мод.");
            }
            string destination = Path.Combine(modsDir, expectedName);
            if (File.Exists(destination))
                throw new IOException("AMW уже установлен. Не перезаписываем существующий мод.");
            string fingerprint;
            using (var stream = File.OpenRead(source))
                fingerprint = Convert.ToHexString(SHA256.HashData(stream));
            File.Copy(source, destination, overwrite: false);
            string receipt = "AMW 1.0.4 Alpha (user imported)\n" +
                "Official source: " + releaseUrl + "\nSHA-256 (local fingerprint, NOT independently verified): " +
                fingerprint + "\nServer: copy the exact same JAR to server/mods.\n";
            File.WriteAllText(Path.Combine(gameDir, "TECHQUEST_AMW_IMPORT.txt"),
                receipt, Encoding.UTF8);
            MessageBox.Show(this,
                "AMW добавлен в этот тестовый профиль.\n" +
                "Для сервера скопируйте тот же JAR в mods.\n" +
                "Требуется проверить GeckoLib, радары, ракеты и конфликт с Incoming/Superb Warfare.\n" +
                "SHA-256 сохранён как локальный отпечаток, не как доказательство подлинности.",
                "AMW: импорт завершён", MessageBoxButtons.OK, MessageBoxIcon.Information);
        }
        catch (Exception ex)
        {
            MessageBox.Show(this, ex.Message,
                "AMW: ошибка импорта", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }

    private async Task CheckForUpdatesAsync()
    {
        if (cancellation != null) return;
        checkUpdates.Enabled = false;
        applyUpdate.Enabled = false;
        downloadExe.Enabled = false;
        availableRelease = null;
        updateAvailable = false;
        try
        {
            releaseStatus.Text = "Проверяем подписанные публикации GitHub…";
            var found = await ReleaseUpdates.CheckAsync(previewUpdates.Checked, CancellationToken.None);
            if (found is null)
            {
                releaseStatus.Text = "Подписанных релизов пока нет. Существующие выпуски можно установить вручную.";
                return;
            }
            availableRelease = found;
            var current = TransactionalMods.GetInstalled(location.Text);
            if (current != null && current.ReleaseTag == found.Tag)
                releaseStatus.Text = "Установлена последняя подписанная версия " + found.Tag;
            else
                releaseStatus.Text = "Доступно проверенное обновление " + found.Tag +
                    ". Установка только по вашему подтверждению.";
            updateAvailable = current != null && current.ReleaseTag != found.Tag;
            applyUpdate.Enabled = updateAvailable;
            downloadExe.Enabled = true;
        }
        catch (Exception ex)
        {
            // Do not log local paths, tokens, HTTP bodies or other private data.
            releaseStatus.Text = "Нет соединения или подпись не прошла проверку: " +
                          ex.GetType().Name;
        }
        finally { checkUpdates.Enabled = true; RefreshProfileStatus(); }
    }

    private async Task ApplyUpdateAsync()
    {
        var release = availableRelease;
        if (release is null) return;
        string root = Path.GetFullPath(location.Text);
        if (MessageBox.Show(this,
            "Установить подписанный " + release.Tag + "?\n" +
            "Будут заменены только управляемые моды. Миры, настройки, скриншоты и сторонние JAR не удаляются.\n" +
            "Закройте Minecraft перед продолжением. При обновлении сервера потребуется такая же версия.",
            "Обновление TechQuest", MessageBoxButtons.YesNo, MessageBoxIcon.Question) != DialogResult.Yes) return;
        cancellation = new CancellationTokenSource();
        SetBusy(true, true);
        try
        {
            if (Directory.Exists(root) &&
                File.Exists(Path.Combine(root, ".techquest", "transaction.json")))
                TransactionalMods.RecoverPending(root);
            var pack = await ReleaseUpdates.DownloadPackAsync(release, cancellation.Token);
            int count = await TransactionalMods.UpdateAsync(root, release, pack,
                new Progress<string>(value => status.Text = value), cancellation.Token);
            MessageBox.Show(this, $"Обновлено файлов: {count}.\nВерсия: {release.Tag}\n" +
                "Запускайте игру через официальный Minecraft Launcher.",
                "TechQuest обновлён", MessageBoxButtons.OK, MessageBoxIcon.Information);
            updateAvailable = false;
            applyUpdate.Enabled = false;
        }
        catch (Exception ex)
        {
            status.Text = "Обновление не применено: " + ex.Message;
            MessageBox.Show(this, "Обновление прервано. При необходимости восстановление будет " +
                "выполнено следующим запуском.\n" + ex.Message,
                "TechQuest: безопасная отмена", MessageBoxButtons.OK, MessageBoxIcon.Warning);
        }
        finally
        {
            SetBusy(false, false);
            cancellation.Dispose();
            cancellation = null;
        }
    }

    private async Task RollbackAsync()
    {
        string root = Path.GetFullPath(location.Text);
        if (MessageBox.Show(this,
            "Вернуть предыдущий набор управляемых модов? Миры и пользовательские настройки не изменятся.",
            "Откат TechQuest", MessageBoxButtons.YesNo, MessageBoxIcon.Question) != DialogResult.Yes) return;
        cancellation = new CancellationTokenSource();
        SetBusy(true, true);
        try
        {
            int count = await TransactionalMods.RollbackAsync(root,
                new Progress<string>(value => status.Text = value), cancellation.Token);
            status.Text = $"Откат завершён. Восстановлено модов: {count}.";
            MessageBox.Show(this, "Предыдущая версия восстановлена. " +
                "Если мир уже открывался в новой версии, его данные не откатывались.",
                "Откат завершён", MessageBoxButtons.OK, MessageBoxIcon.Information);
        }
        catch (Exception ex)
        {
            status.Text = "Откат не выполнен: " + ex.Message;
            MessageBox.Show(this, ex.Message, "Ошибка отката",
                MessageBoxButtons.OK, MessageBoxIcon.Warning);
        }
        finally
        {
            SetBusy(false, false);
            cancellation.Dispose();
            cancellation = null;
        }
    }

    private async Task DownloadNewInstallerAsync()
    {
        var release = availableRelease;
        if (release is null) return;
        cancellation = new CancellationTokenSource();
        SetBusy(true, true);
        try
        {
            string file = await ReleaseUpdates.DownloadInstallerAsync(release, baseDir, cancellation.Token);
            status.Text = "Новый EXE скачан и проверен по подписанному SHA-256.";
            MessageBox.Show(this, "Новый EXE проверен и сохранён:\n" + file + "\n\n" +
                "Он не запускается автоматически. Закройте старый установщик и запустите новый вручную.",
                "Подписанный установщик", MessageBoxButtons.OK, MessageBoxIcon.Information);
        }
        catch (Exception ex)
        {
            status.Text = "Новый EXE не скачан: " + ex.GetType().Name;
            MessageBox.Show(this, ex.Message, "Ошибка проверки EXE",
                MessageBoxButtons.OK, MessageBoxIcon.Warning);
        }
        finally
        {
            SetBusy(false, false);
            cancellation.Dispose();
            cancellation = null;
        }
    }

    private static void StageFirstPartyCompatibilityJar(string staging)
    {
        // Preserve the existing Create-IC2 recipes and Better Zoom startup Mixin.
        // Always stage our verified current JAR rather than an older saved copy.
        const string filename = "techquest-compat-1.0.0.jar";
        using var pack = GetEmbeddedPack();
        using var archive = new ZipArchive(pack, ZipArchiveMode.Read);
        var item = archive.GetEntry("overrides/mods/" + filename)
            ?? throw new InvalidDataException("Встроенный TechQuest Compatibility JAR отсутствует.");
        if (item.Length < 64 || item.Length > 8 * 1024 * 1024)
            throw new InvalidDataException("Некорректный размер TechQuest Compatibility JAR.");
        using var input = item.Open();
        using var output = File.Create(Path.Combine(staging, filename));
        input.CopyTo(output);
    }

    private async Task InstallAsync()
    {
        string target = Path.GetFullPath(location.Text);
        string mods = Path.Combine(target, "mods");
        string vanillaRoot = Path.GetFullPath(Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), ".minecraft"));
        if (string.Equals(target.TrimEnd(Path.DirectorySeparatorChar),
                vanillaRoot.TrimEnd(Path.DirectorySeparatorChar),
                StringComparison.OrdinalIgnoreCase))
        {
            MessageBox.Show(this, "Выберите отдельный профиль TechQuest, а не общий .minecraft.",
                "Безопасность установки", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }
        if (Directory.Exists(mods) && Directory.EnumerateFiles(mods, "*.jar").Any())
        {
            MessageBox.Show(this, "В выбранной папке уже есть моды. Для безопасности выберите новую пустую папку.",
                "Нельзя смешивать модпаки", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }
        cancellation = new CancellationTokenSource();
        SetBusy(true, true);
        string staging = Path.Combine(target, ".techquest-download-" + Guid.NewGuid().ToString("N"));
        try
        {
            using var pack = GetEmbeddedPack();
            var list = LoadManifest(pack);
            Directory.CreateDirectory(staging);
            progress.Minimum = 0;
            progress.Maximum = list.Count;
            progress.Value = 0;
            int completed = 0;
            IProgress<(int done, string name)> updates = new Progress<(int done, string name)>(
                item =>
                {
                    progress.Value = Math.Min(item.done, list.Count);
                    status.Text = $"Загружено {item.done}/{list.Count}: {item.name}";
                });
            // Preserve bounded parallel downloads and retries from main.
            await Parallel.ForEachAsync(list, new ParallelOptions
            {
                MaxDegreeOfParallelism = 5,
                CancellationToken = cancellation.Token
            }, async (mod, token) =>
            {
                await DownloadWithRetryAsync(mod, Path.Combine(staging, mod.Name), token);
                updates.Report((Interlocked.Increment(ref completed), mod.Name));
            });
            StageFirstPartyCompatibilityJar(staging);
            cancellation.Token.ThrowIfCancellationRequested();
            if (Directory.Exists(mods)) Directory.Delete(mods, recursive: false);
            Directory.Move(staging, mods);
            InstallGuideOverrides(target);
            using (var embedded = GetEmbeddedPack())
                TransactionalMods.RecordInitialInstallation(target, embedded);
            installedGameDir = target;
            File.WriteAllText(Path.Combine(target, "TechQuest_НАСТРОЙКА.txt"),
                "TechQuest 0.3.3 Alpha\n" +
                "Minecraft Java 1.21.1, NeoForge 21.1.264.\n" +
                "Установите официальный NeoForge (кнопка в установщике).\n" +
                "Minecraft Launcher -> Установки -> профиль NeoForge -> Папка игры:\n" +
                target + "\nJava 21. Не используйте ванильный профиль.\n", Encoding.UTF8);
            status.Text = $"Установлено {list.Count} файлов. Далее установите NeoForge и настройте профиль Minecraft.";
            MessageBox.Show(this,
                $"Моды TechQuest Optimized установлены!\n\n" +
                target + "\n\nТеперь нажмите «Установить NeoForge», затем выберите эту папку " +
                "в официальном Minecraft Launcher (Установки → профиль NeoForge → Папка игры).",
                "Установка завершена", MessageBoxButtons.OK, MessageBoxIcon.Information);
        }
        catch (OperationCanceledException)
        {
            status.Text = "Установка отменена.";
        }
        catch (Exception ex)
        {
            status.Text = "Ошибка: " + ex.Message;
            MessageBox.Show(this, ex.Message,
                "Ошибка установки", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
        finally
        {
            if (Directory.Exists(staging))
            {
                try { Directory.Delete(staging, recursive: true); } catch (IOException) { }
            }
            SetBusy(false, false);
            cancellation?.Dispose();
            cancellation = null;
            RefreshProfileStatus();
        }
    }

    private async Task NeoForgeAsync()
    {
        using var folder = new FolderBrowserDialog {
            Description = "Выберите папку официального Minecraft Launcher (.minecraft), где уже установлена обычная 1.21.1. Это НЕ отдельная папка модпака.",
            SelectedPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), ".minecraft"),
            ShowNewFolderButton = false
        };
        if (folder.ShowDialog(this) != DialogResult.OK) return;
        string launcherRoot = Path.GetFullPath(folder.SelectedPath);
        cancellation = new CancellationTokenSource();
        SetBusy(true, true);
        try
        {
            using var manifest = Assembly.GetExecutingAssembly().GetManifestResourceStream("TechQuest.NeoForge.bootstrap.json")
                ?? throw new InvalidDataException("Не найден закреплённый план установки NeoForge.");
            var bootstrap = new NeoForgeBootstrap(Client, text => status.Text = text);
            string destination = await bootstrap.PrepareAsync(NeoForgeBootstrap.ReadPlan(manifest), launcherRoot,
                Path.Combine(baseDir, "neoforge-" + NeoForgeVersion), cancellation.Token);
            try
            {
                var start = new ProcessStartInfo("javaw.exe") {
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    WorkingDirectory = Path.GetDirectoryName(destination)!
                };
                start.ArgumentList.Add("-jar");
                start.ArgumentList.Add(destination);
                Process.Start(start);
                status.Text = "NeoForge открыт. Выберите Install client и папку Launcher: " + launcherRoot;
                MessageBox.Show(this, "Установщик и 70 библиотек проверены.\nВ окне NeoForge выберите Install client и эту папку:\n" +
                    launcherRoot + "\n\nПосле установки укажите отдельную папку модпака как Game Directory в Minecraft Launcher.",
                    "Далее — официальный установщик", MessageBoxButtons.OK, MessageBoxIcon.Information);
            }
            catch (Exception)
            {
                status.Text = "Для установки NeoForge нужна Java 21.";
                MessageBox.Show(this,
                    "Не удалось открыть установщик NeoForge через Java.\n" +
                    "Установите Java 21 и запустите NeoForge installer двойным щелчком.\n\n" +
                    "Проверенный установщик сохранён в:\n" + destination,
                    "Требуется Java 21", MessageBoxButtons.OK, MessageBoxIcon.Information);
                Process.Start(new ProcessStartInfo("https://adoptium.net/temurin/releases/?version=21")
                    { UseShellExecute = true });
            }
        }
        catch (OperationCanceledException)
        {
            status.Text = "Подготовка NeoForge отменена. Проверенные библиотеки сохранены для повторной попытки.";
        }
        catch (Exception ex)
        {
            status.Text = "Ошибка установки NeoForge: " + ex.Message;
            MessageBox.Show(this, ex.Message, "Ошибка NeoForge", MessageBoxButtons.OK,
                MessageBoxIcon.Error);
        }
        finally
        {
            SetBusy(false, false);
            cancellation?.Dispose();
            cancellation = null;
        }
    }
}
