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
    private static void Main()
    {
        ApplicationConfiguration.Initialize();
        Application.Run(new InstallerForm());
    }
}

internal sealed class InstallerForm : Form
{
    private const string NeoForgeVersion = "21.1.259";
    private const string NeoForgeUrl = "https://maven.neoforged.net/releases/net/neoforged/neoforge/21.1.259/neoforge-21.1.259-installer.jar";
    private static readonly HttpClient Client = new() { Timeout = TimeSpan.FromMinutes(5) };

    private readonly RadioButton lite = new() { Text = "Lite — для слабых ПК (рекомендуется)", Checked = true, AutoSize = true };
    private readonly RadioButton full = new() { Text = "Full — все шейдерные возможности", AutoSize = true };
    private readonly TextBox location = new() { Width = 540 };
    private readonly Button browse = new() { Text = "Обзор…", Width = 110 };
    private readonly Button install = new() { Text = "1. Установить моды", Width = 205, Height = 45 };
    private readonly Button neoforge = new() { Text = "2. Установить NeoForge", Width = 205, Height = 45 };
    private readonly Button openFolder = new() { Text = "Открыть папку", Width = 150, Height = 37 };
    private readonly Button help = new() { Text = "Инструкция", Width = 130, Height = 37 };
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
        Height = 620;
        MinimumSize = new Size(760, 600);
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
        var heading = new Label { Text = "Выберите клиентскую версию", Left = 32, Top = 126,
            Width = 700, Height = 30, Font = new Font("Segoe UI", 12F, FontStyle.Bold) };
        lite.Location = new Point(36, 166);
        full.Location = new Point(36, 197);
        lite.CheckedChanged += (_, _) => UpdateTarget();
        full.CheckedChanged += (_, _) => UpdateTarget();

        var liteDesc = new Label { Text = "Без Iris; Sodium, ImmediatelyFast, More Culling, BadOptimizations, Dynamic FPS.",
            Left = 57, Top = 228, Width = 685, Height = 30, ForeColor = Color.FromArgb(153, 172, 193) };
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
            Text = "В оба варианта входят одинаковые игровые моды. Lite подключается к общему серверу Full.\n" +
                   "Моды скачиваются по HTTPS с проверкой SHA-512 / SHA-1.",
            Left = 32, Top = 354, Width = 710, Height = 54,
            ForeColor = Color.FromArgb(175, 194, 212)
        };

        install.Location = new Point(32, 421);
        neoforge.Location = new Point(246, 421);
        openFolder.Location = new Point(32, 488);
        help.Location = new Point(190, 488);
        cancel.Location = new Point(330, 488);
        progress.Location = new Point(32, 535);
        status.Location = new Point(32, 557);
        install.BackColor = Color.FromArgb(168, 227, 117);
        install.ForeColor = Color.FromArgb(18, 33, 18);
        neoforge.BackColor = Color.FromArgb(41, 56, 79);
        neoforge.ForeColor = Color.White;
        foreach (var button in new[] { install, neoforge, openFolder, browse, cancel, help })
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
        Controls.AddRange(new Control[] {
            title, subtitle, heading, lite, full, liteDesc, pathHeading, location,
            browse, safety, install, neoforge, openFolder, help, cancel, progress, status
        });
        UpdateTarget();
    }

    private void UpdateTarget()
    {
        location.Text = Path.Combine(baseDir, lite.Checked ? "Lite" : "Full");
    }

    private void SetBusy(bool busy, bool cancellable)
    {
        install.Enabled = !busy;
        neoforge.Enabled = !busy;
        browse.Enabled = !busy;
        lite.Enabled = !busy;
        full.Enabled = !busy;
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
            "4. Откройте официальный Minecraft Launcher → Установки → NeoForge 21.1.259 → Изменить.\n" +
            "5. В «Папка игры / Game Directory» укажите выбранный здесь путь.\n" +
            "6. Запускайте профиль NeoForge, НЕ обычную ванильную Minecraft 1.21.1.\n\n" +
            "Lite: графика Fast, прорисовка 4–6 чанков, без шейдеров, 4–6 ГБ RAM\n" +
            "(если системной памяти достаточно). Full: ориентир 8 ГБ RAM.\n\n" +
            "Клиент Lite и Full подключаются к одному серверу. Сборка alpha: протестируйте новый мир.",
            "Как запустить TechQuest", MessageBoxButtons.OK, MessageBoxIcon.Information);
    }

    private static Stream GetEmbeddedPack(bool isLite)
    {
        string name = isLite ? "TechQuest.Lite.mrpack" : "TechQuest.Full.mrpack";
        return Assembly.GetExecutingAssembly().GetManifestResourceStream(name)
            ?? throw new InvalidDataException("Сборка " + name + " не встроена в установщик.");
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
                 url.Host != "raw.githubusercontent.com"))
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
        bool selectedLite = lite.Checked;
        cancellation = new CancellationTokenSource();
        SetBusy(true, true);
        string staging = Path.Combine(target, ".techquest-download-" + Guid.NewGuid().ToString("N"));
        try
        {
            using var pack = GetEmbeddedPack(selectedLite);
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
            installedGameDir = target;
            if (selectedLite)
            {
                var optionsFile = Path.Combine(target, "options.txt");
                if (!File.Exists(optionsFile))
                    File.WriteAllText(optionsFile,
                        "graphicsMode:fast\nrenderDistance:6\nsimulationDistance:5\n" +
                        "entityDistanceScaling:0.5\nparticles:2\nmaxFps:60\n" +
                        "biomeBlendRadius:0\nmipmapLevels:1\n", new UTF8Encoding(false));
            }
            File.WriteAllText(Path.Combine(target, "TechQuest_НАСТРОЙКА.txt"),
                "TechQuest " + (selectedLite ? "Lite" : "Full") + "\n" +
                "Minecraft Java 1.21.1, NeoForge 21.1.259.\n" +
                "Установите официальный NeoForge (кнопка в установщике).\n" +
                "Minecraft Launcher -> Установки -> профиль NeoForge -> Папка игры:\n" +
                target + "\nJava 21. Не используйте ванильный профиль.\n", Encoding.UTF8);
            status.Text = $"Установлено {list.Count} файлов. Далее установите NeoForge и настройте профиль Minecraft.";
            MessageBox.Show(this,
                $"Моды TechQuest {(selectedLite ? "Lite" : "Full")} установлены!\n\n" +
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
        SetBusy(true, false);
        try
        {
            status.Text = "Загрузка официального установщика NeoForge...";
            var destination = Path.Combine(Path.GetTempPath(), $"neoforge-{NeoForgeVersion}-installer.jar");
            var url = new Uri(NeoForgeUrl);
            var sumText = await Client.GetStringAsync(NeoForgeUrl + ".sha512");
            var expectedHash = sumText.Split((char[]?)null,
                StringSplitOptions.RemoveEmptyEntries)[0].Trim();
            if (expectedHash.Length != 128) throw new InvalidDataException("Неверный SHA-512 NeoForge");
            var bytes = await Client.GetByteArrayAsync(url);
            if (!SHA512.HashData(bytes).AsSpan().SequenceEqual(Convert.FromHexString(expectedHash)))
                throw new InvalidDataException("SHA-512 NeoForge не совпал. Запуск отменён.");
            await File.WriteAllBytesAsync(destination, bytes);
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
                status.Text = "Установщик NeoForge открыт. Выберите Install client.";
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
        catch (Exception ex)
        {
            status.Text = "Ошибка установки NeoForge: " + ex.Message;
            MessageBox.Show(this, ex.Message, "Ошибка NeoForge", MessageBoxButtons.OK,
                MessageBoxIcon.Error);
        }
        finally { SetBusy(false, false); }
    }
}
