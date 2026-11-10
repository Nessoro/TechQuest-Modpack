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

internal sealed class InstallerForm : Form
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
    private readonly ProgressBar progress = new() { Width = 695, Height = 19 };
    private readonly Label status = new() { Text = "Готово к установке. Minecraft Launcher и Java 21 устанавливаются отдельно.", AutoSize = false, Width = 710, Height = 45 };
    private CancellationTokenSource? cancellation;
    private readonly string baseDir = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "TechQuest");
    private string? installedGameDir;

    internal InstallerForm()
    {
        Text = "TechQuest — установщик Minecraft 1.21.1";
        Width = 800;
        Height = 680;
        MinimumSize = new Size(760, 660);
        StartPosition = FormStartPosition.CenterScreen;
        BackColor = Color.FromArgb(15, 22, 34);
        ForeColor = Color.WhiteSmoke;
        Font = new Font("Segoe UI", 10F);
        FormBorderStyle = FormBorderStyle.FixedDialog;
        MaximizeBox = false;

        var title = new Label { Text = "TECHQUEST  ·  INSTALLER", Left = 30, Top = 26,
            Width = 715, Height = 43, ForeColor = Color.FromArgb(172, 236, 125),
            Font = new Font("Segoe UI", 21F, FontStyle.Bold) };
        var subtitle = new Label { Text = "Minecraft Java 1.21.1  •  NeoForge " + NeoForgeVersion +
            "  •  BuildCraft + IndustrialCraft", Left = 32, Top = 78, Width = 710, Height = 30,
            ForeColor = Color.FromArgb(175, 194, 212) };
        var heading = new Label { Text = "TechQuest 0.3.3 — приключения, физика и оптимизация", Left = 32, Top = 126,
            Width = 700, Height = 30, Font = new Font("Segoe UI", 12F, FontStyle.Bold) };
        var liteDesc = new Label { Text = "Сохранены все игровые моды. Ускорение: Sodium, ImmediatelyFast, More Culling,",
            Left = 36, Top = 168, Width = 706, Height = 30, ForeColor = Color.FromArgb(153, 172, 193) };
        var moreDesc = new Label { Text = "BadOptimizations, Dynamic FPS, FerriteCore и ModernFix. Без Iris и шейдеров.",
            Left = 36, Top = 197, Width = 706, Height = 30, ForeColor = Color.FromArgb(153, 172, 193) };
        var pathHeading = new Label { Text = "Папка игры (новая, без других модов)", Left = 32, Top = 280,
            Width = 690, Height = 26, Font = new Font("Segoe UI", 11F, FontStyle.Bold) };
        location.Location = new Point(32, 311);
        browse.Location = new Point(596, 309);
        browse.Click += (_, _) =>
        {
            using var dialog = new FolderBrowserDialog {
                Description = "Выберите отдельную пустую папку для TechQuest",
                SelectedPath = Directory.Exists(location.Text) ? location.Text : baseDir,
                ShowNewFolderButton = true
            };
            if (dialog.ShowDialog(this) == DialogResult.OK)
                location.Text = dialog.SelectedPath;
        };

        var safety = new Label {
            Text = "Единый набор игровых модов для любого ПК и общего сервера.\n" +
                   "Моды скачиваются по HTTPS с проверкой SHA-512 / SHA-1.",
            Left = 32, Top = 354, Width = 710, Height = 54,
            ForeColor = Color.FromArgb(175, 194, 212)
        };

        install.Location = new Point(32, 421);
        neoforge.Location = new Point(246, 421);
        openFolder.Location = new Point(32, 488);
        help.Location = new Point(190, 488);
        cancel.Location = new Point(330, 488);
        importAmw.Location = new Point(462, 488);
        progress.Location = new Point(32, 535);
        status.Location = new Point(32, 557);
        install.BackColor = Color.FromArgb(168, 227, 117);
        install.ForeColor = Color.FromArgb(18, 33, 18);
        neoforge.BackColor = Color.FromArgb(41, 56, 79);
        neoforge.ForeColor = Color.White;
        foreach (var button in new[] { install, neoforge, openFolder, browse, cancel, help, importAmw })
        {
            button.FlatStyle = FlatStyle.Flat;
            button.FlatAppearance.BorderSize = 0;
        }

        install.Click += async (_, _) => await InstallAsync();
        neoforge.Click += async (_, _) => await NeoForgeAsync();
        openFolder.Click += (_, _) => {
            var path = installedGameDir ?? location.Text;
            if (Directory.Exists(path))
                Process.Start(new ProcessStartInfo(path) { UseShellExecute = true });
        };
        cancel.Click += (_, _) => cancellation?.Cancel();
        help.Click += (_, _) => ShowInstructions();
        importAmw.Click += (_, _) => ImportAcceleratedMcWarfare();
        Controls.AddRange(new Control[] {
            title, subtitle, heading, liteDesc, moreDesc, pathHeading, location,
            browse, safety, install, neoforge, openFolder, help, cancel, importAmw, progress, status
        });
        location.Text = Path.Combine(baseDir, "TechQuest_0.3.3_Alpha");
    }

    private void SetBusy(bool busy, bool cancellable)
    {
        install.Enabled = !busy;
        neoforge.Enabled = !busy;
        importAmw.Enabled = !busy;
        browse.Enabled = !busy;
        location.ReadOnly = busy;
        cancel.Enabled = busy && cancellable;
        UseWaitCursor = busy;
    }

    private void ShowInstructions()
    {
        MessageBox.Show(this,
            "1. Нажмите «Установить моды»; Python и консоль не нужны.\n" +
            "2. Установите Java 21, если её нет на компьютере.\n" +
            "3. Нажмите «Установить NeoForge», в его окне выберите Install client.\n" +
            "4. Откройте официальный Minecraft Launcher → Установки → NeoForge 21.1.264 → Изменить.\n" +
            "5. В «Папка игры / Game Directory» укажите выбранный здесь путь.\n" +
            "6. Запускайте профиль NeoForge, НЕ обычную ванильную Minecraft 1.21.1.\n" +
            "7. AMW (необязательно): скачайте официальный JAR с CurseForge, затем нажмите «3. Добавить AMW».\n" +
            "   Для сервера положите тот же JAR в mods и проверьте совместимость с Incoming.\n" +
            "Оптимизированный профиль: графика Fast, 4–6 чанков, без шейдеров,\n" +
            "6 ГБ RAM при наличии 16 ГБ системной памяти.\n\n" +
            "В игре: Xaero Minimap/World Map, здоровье мобов Health Indicator TXF (HP цифрами),\n" +
            "книга «Путеводитель TechQuest» через Patchouli (в творческом режиме).\n" +
            "В режиме выживания руководство выдаётся при первом входе в мир.\n" +
            "Project MMO: большой список навыков скрыт; Left Alt — показать/скрыть.\n\n" +
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
                 archive.GetEntry("overrides/mods/techquest-compat-1.0.0.jar") is null)
                return 7;
            string probe = Path.Combine(Path.GetTempPath(), "TechQuest-self-test-" + Guid.NewGuid().ToString("N"));
            try
            {
                InstallGuideOverrides(probe);
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
                if (fileNames.Any(n => n.StartsWith("pmmo-", StringComparison.OrdinalIgnoreCase)))
                {
                    string pmmoConfig = Path.Combine(probe, "config", "pmmo-client.toml");
                    string pmmoText = File.ReadAllText(pmmoConfig);
                    if (!pmmoText.Contains("\"Display Skill List\" = false") ||
                        !pmmoText.Contains("\"Skill List Use Icons\" = true") ||
                        !pmmoText.Contains("\"Display Gain List\" = true")) return 15;
                    File.WriteAllText(pmmoConfig, "existing-player-pmmo-settings");
                    InstallGuideOverrides(probe);
                    if (File.ReadAllText(pmmoConfig) != "existing-player-pmmo-settings") return 16;
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

    private static async Task DownloadCheckedAsync(ModFile file, string destination, CancellationToken token)
    {
        using var response = await Client.GetAsync(file.Url, HttpCompletionOption.ResponseHeadersRead, token);
        response.EnsureSuccessStatusCode();
        await using (var input = await response.Content.ReadAsStreamAsync(token))
        await using (var output = File.Create(destination))
            await input.CopyToAsync(output, token);
        var info = new FileInfo(destination);
        if (info.Length != file.Size) throw new InvalidDataException("Неверный размер " + file.Name);
        if (file.Sha512 is not null)
        {
            using var sha = SHA512.Create();
            using var stream = File.OpenRead(destination);
            if (!sha.ComputeHash(stream).AsSpan().SequenceEqual(Convert.FromHexString(file.Sha512)))
                throw new InvalidDataException("Ошибка SHA-512 у " + file.Name);
        }
        if (file.Sha1 is not null)
        {
            using var sha = SHA1.Create();
            using var stream = File.OpenRead(destination);
            if (!sha.ComputeHash(stream).AsSpan().SequenceEqual(Convert.FromHexString(file.Sha1)))
                throw new InvalidDataException("Ошибка SHA-1 у " + file.Name);
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
                relative == "config/pmmo-client.toml" ||
                relative == "config/incoming-client.toml" ||
                relative == "config/explosionoverhaul/explosionoverhaul-client.toml" ||
                relative == "config/jade/plugins.json" ||
                relative == "config/healthindicatortxf.json5" ||
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

    private async Task InstallAsync()
    {
        string target = Path.GetFullPath(location.Text);
        string mods = Path.Combine(target, "mods");
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
            for (int n = 0; n < list.Count; n++)
            {
                cancellation.Token.ThrowIfCancellationRequested();
                var mod = list[n];
                status.Text = $"Загрузка {n + 1}/{list.Count}: {mod.Name}";
                await DownloadCheckedAsync(mod, Path.Combine(staging, mod.Name), cancellation.Token);
                progress.Value = n + 1;
            }
            if (Directory.Exists(mods)) Directory.Delete(mods, recursive: false);
            Directory.Move(staging, mods);
            InstallGuideOverrides(target);
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
