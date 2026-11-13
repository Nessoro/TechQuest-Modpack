using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace TechQuestTEST;

internal static class Program
{
    [STAThread]
    private static void Main()
    {
        ApplicationConfiguration.Initialize();
        Application.Run(new TestInstaller());
    }
}

internal sealed record DownloadFile(string Name, string FileName, Uri Url, string Algorithm,
    string Checksum, long ExpectedBytes = 0);

internal sealed class TestInstaller : Form
{
    private const string IncomingSha256 = "445c8549f6fec60758b841313adc8d1b58c3770eb4e08bb04c3845e22690d53f";
    private const string UltimineSha1 = "c96a7cc0b52bf919660ea61c1536cebd9d5773b3";
    private const string FtbMaven = "https://maven.ftb.dev/releases/dev/ftb/mods/";
    private static readonly HttpClient Client = new() { Timeout = TimeSpan.FromMinutes(8) };
    private static readonly string Root = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "TechQuest", "TEST");

    private readonly ComboBox scenarios = new() { DropDownStyle = ComboBoxStyle.DropDownList, Width = 495 };
    private readonly Button install = new() { Text = "Установить TEST отдельно", Height = 44, Width = 240 };
    private readonly Button open = new() { Text = "Открыть папку TEST", Height = 44, Width = 210 };
    private readonly ProgressBar progress = new() { Width = 500, Height = 22 };
    private readonly Label status = new() { AutoSize = true, MaximumSize = new Size(580, 0), Text = "Готово к установке" };
    private readonly TextBox logs = new() { Multiline = true, ReadOnly = true, ScrollBars = ScrollBars.Vertical, Width = 570, Height = 225 };
    private readonly string[] names = {
        "TEST_ALL — все 4 мода (Collapse OFF)",
        "TEST_VEIN — только Simple Vein Miner",
        "TEST_ULTIMINE — только FTB Ultimine",
        "TEST_PHYSICS_OFF — только Physics (Collapse OFF)",
        "TEST_PHYSICS_ON — только Physics (Collapse ON)",
        "TEST_INCOMING — только Incoming"
    };

    public TestInstaller()
    {
        Text = "TEST — TechQuest isolated mod test";
        Font = new Font("Segoe UI", 10);
        ClientSize = new Size(620, 560);
        MinimumSize = MaximumSize = Size;
        MaximizeBox = false;
        StartPosition = FormStartPosition.CenterScreen;

        var stack = new FlowLayoutPanel {
            Dock = DockStyle.Fill, FlowDirection = FlowDirection.TopDown,
            WrapContents = false, Padding = new Padding(18), AutoScroll = true
        };
        Controls.Add(stack);
        stack.Controls.Add(new Label { AutoSize = true, Font = new Font(Font, FontStyle.Bold),
            Text = "TEST: 4 игровых мода + необходимые библиотеки" });
        stack.Controls.Add(new Label { AutoSize = true, MaximumSize = new Size(560, 0),
            Text = "Minecraft 1.21.1 / NeoForge 21.1.264 / Java 21. " +
                   "Профили TEST не используют папку, миры и конфиги основной TechQuest." });
        stack.Controls.Add(new Label { AutoSize = true, Text = "Сценарий для диагностики:" });
        scenarios.Items.AddRange(names.Cast<object>().ToArray());
        scenarios.SelectedIndex = 0;
        stack.Controls.Add(scenarios);
        stack.Controls.Add(new Label { AutoSize = true, MaximumSize = new Size(560, 0),
            Text = "Все файлы устанавливаются в " + Root + Environment.NewLine +
                   "Отдельное имя папки для каждого сценария. Повторно существующие профили не изменяются." });
        var actions = new FlowLayoutPanel { Width = 580, Height = 54 };
        actions.Controls.Add(install);
        actions.Controls.Add(open);
        stack.Controls.Add(actions);
        stack.Controls.Add(progress);
        stack.Controls.Add(status);
        stack.Controls.Add(logs);

        install.Click += async (_, _) => await RunInstallAsync();
        open.Click += (_, _) => {
            Directory.CreateDirectory(Root);
            System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo(Root) { UseShellExecute = true });
        };
        Client.DefaultRequestHeaders.UserAgent.ParseAdd("TechQuest-TEST-Installer/1.0");
    }

    private void Log(string value)
    {
        logs.AppendText(value + Environment.NewLine);
        status.Text = value;
    }

    private async Task RunInstallAsync()
    {
        install.Enabled = false;
        scenarios.Enabled = false;
        string? staging = null;
        try
        {
            var scenario = names[scenarios.SelectedIndex].Split(' ')[0];
            Directory.CreateDirectory(Root);
            if ((File.GetAttributes(Root) & FileAttributes.ReparsePoint) != 0)
                throw new IOException("Папка TEST не может быть ссылкой/перенаправлением.");
            var target = Path.Combine(Root, scenario);
            if (Directory.Exists(target) || File.Exists(target))
                throw new IOException("Этот профиль уже существует: " + target +
                    ". Для сохранности мира и настроек установщик ничего в нём не изменяет.");
            staging = Path.Combine(Root, ".staging-" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(Path.Combine(staging, "mods"));
            progress.Value = 0;

            var specs = new List<DownloadFile>();
            if (scenario == "TEST_ALL" || scenario == "TEST_VEIN")
                specs.Add(await Modrinth("Simple Vein Miner", "PrOVZx3c"));
            if (scenario == "TEST_ALL" || scenario == "TEST_ULTIMINE")
            {
                specs.Add(await FtbArtifact("FTB Ultimine", "ftb-ultimine-neoforge", "2101.1.15", UltimineSha1));
                specs.Add(await FtbArtifact("FTB Library", "ftb-library-neoforge", "2101.1.37"));
                specs.Add(await Modrinth("Architectury API", "1IiqEQGl"));
            }
            if (scenario is "TEST_ALL" or "TEST_PHYSICS_OFF" or "TEST_PHYSICS_ON")
                specs.Add(await Modrinth("Physics Mod Lite", "wudTG1nk"));
            if (scenario == "TEST_ALL" || scenario == "TEST_INCOMING")
                specs.Add(new DownloadFile("Incoming", "incoming-3.10.4.jar",
                    new Uri("https://github.com/zentixua/incoming/releases/download/v3.10.4/incoming-3.10.4.jar"),
                    "SHA256", IncomingSha256, 23250455));

            if (specs.Select(x => x.FileName).Distinct(StringComparer.OrdinalIgnoreCase).Count() != specs.Count)
                throw new InvalidDataException("В сценарии обнаружены повторяющиеся имена модов.");
            progress.Maximum = specs.Count;
            Log("Подготовка " + scenario + " (" + specs.Count + " JAR)...");
            foreach (var item in specs)
            {
                Log("Загрузка и проверка: " + item.Name);
                var dest = Path.Combine(staging, "mods", item.FileName);
                await InstallJarAsync(item, dest);
                progress.Value++;
            }

            if (scenario is "TEST_ALL" or "TEST_PHYSICS_OFF" or "TEST_PHYSICS_ON")
            {
                var configDir = Path.Combine(staging, "config", "physicsmod");
                Directory.CreateDirectory(configDir);
                bool collapse = scenario == "TEST_PHYSICS_ON";
                File.WriteAllText(Path.Combine(configDir, "physics_server_config.json"),
                    "{\n  \"collapse\": " + (collapse ? "true" : "false") +
                    ",\n  \"dropBlocks\": true,\n  \"maxCollapseObjects\": 100,\n  \"collapseSpeed\": 10\n}\n",
                    new UTF8Encoding(false));
            }
            File.WriteAllText(Path.Combine(staging, "TEST_README.txt"),
                Instructions(scenario, target), new UTF8Encoding(false));
            Directory.Move(staging, target);
            staging = null;
            Log("Установка завершена: " + target);
            MessageBox.Show(this,
                "Профиль " + scenario + " установлен отдельно.\n\n" +
                "Создайте в официальном Minecraft Launcher отдельную установку TEST " +
                "для NeoForge 21.1.264 и задайте папку игры:\n" + target +
                "\n\nОсновная TechQuest не изменена.",
                "TEST готов", MessageBoxButtons.OK, MessageBoxIcon.Information);
        }
        catch (Exception ex)
        {
            Log("Ошибка: " + ex.Message);
            MessageBox.Show(this, ex.Message, "TEST: установка не завершена",
                MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
        finally
        {
            if (staging != null && Directory.Exists(staging))
                try { Directory.Delete(staging, true); } catch (IOException) { }
            install.Enabled = true;
            scenarios.Enabled = true;
        }
    }

    private static string Instructions(string scenario, string target)
    {
        return "TECHQUEST TEST — ISOLATED TEST PROFILE\n" +
            "Minecraft Java 1.21.1 / NeoForge 21.1.264 / Java 21\n" +
            "Scenario: " + scenario + "\nGame Directory: " + target + "\n\n" +
            "1. В официальном Minecraft Launcher откройте Установки -> Новая установка.\n" +
            "2. Название: " + scenario + ". Выберите версию NeoForge 21.1.264.\n" +
            "3. В поле Папка игры (Game Directory) установите путь выше.\n" +
            "4. Запустите именно новый профиль. Не меняйте папку TechQuest.\n" +
            "5. Создайте НОВЫЙ тестовый мир. Для старого мира используйте КОПИЮ,\n" +
            "   перенесённую только в этот профиль в папку saves.\n\n" +
            "DIAGNOSTICS:\n" +
            "- Поставьте столб из 3 блоков камня и сломайте нижний БЕЗ специальных клавиш.\n" +
            "- Повторите с землёй, деревом и рудой, отметьте, падают или исчезают блоки.\n" +
            "- Simple Vein Miner: Left Shift удержание, Right Shift переключает режим.\n" +
            "- FTB Ultimine: проверьте назначенную клавишу через меню управления.\n" +
            "- Physics Collapse ON/OFF: сравните два разных сценария на НОВЫХ мирах.\n" +
            "- TEST_ALL включает все 4 игровых мода; FTB Library и Architectury — обязательные библиотеки.\n" +
            "- Внешние JAR загружаются с первичных источников с проверкой хеша.\n" +
            "- В основной папке TechQuest установщик не читает и не записывает файлы.\n";
    }

    private static async Task<DownloadFile> Modrinth(string name, string versionId)
    {
        using var response = await Client.GetAsync("https://api.modrinth.com/v2/version/" + Uri.EscapeDataString(versionId));
        response.EnsureSuccessStatusCode();
        using var doc = JsonDocument.Parse(await response.Content.ReadAsStreamAsync());
        var root = doc.RootElement;
        if (!root.GetProperty("game_versions").EnumerateArray().Any(x => x.GetString() == "1.21.1") ||
            !root.GetProperty("loaders").EnumerateArray().Any(x => x.GetString() == "neoforge"))
            throw new InvalidDataException(name + ": опубликованная версия не для NeoForge 1.21.1.");
        var entries = root.GetProperty("files").EnumerateArray().ToList();
        var file = entries.FirstOrDefault(x => x.TryGetProperty("primary", out var p) && p.GetBoolean());
        if (file.ValueKind != JsonValueKind.Object)
            file = entries.FirstOrDefault();
        if (file.ValueKind != JsonValueKind.Object)
            throw new InvalidDataException(name + ": файл отсутствует.");
        var url = new Uri(file.GetProperty("url").GetString()!);
        if (url.Scheme != Uri.UriSchemeHttps || url.Host != "cdn.modrinth.com")
            throw new InvalidDataException(name + ": недопустимый источник загрузки.");
        var filename = file.GetProperty("filename").GetString()!;
        if (!IsSafeJar(filename))
            throw new InvalidDataException(name + ": некорректное имя JAR.");
        var hash = file.GetProperty("hashes").GetProperty("sha512").GetString()!;
        if (!IsHex(hash, 128))
            throw new InvalidDataException(name + ": отсутствует надёжный SHA-512.");
        return new DownloadFile(name, filename, url, "SHA512", hash, file.GetProperty("size").GetInt64());
    }

    private static async Task<DownloadFile> FtbArtifact(string name, string artifact, string version,
        string? pinnedHash = null)
    {
        var file = artifact + "-" + version + ".jar";
        var baseUrl = FtbMaven + artifact + "/" + version + "/" + file;
        var hash = pinnedHash;
        if (hash == null)
        {
            using var response = await Client.GetAsync(baseUrl + ".sha1");
            response.EnsureSuccessStatusCode();
            hash = (await response.Content.ReadAsStringAsync()).Trim().Split(' ', '\t', '\r', '\n')[0];
        }
        if (!IsHex(hash, 40))
            throw new InvalidDataException(name + ": хеш FTB Maven неверный.");
        return new DownloadFile(name, file, new Uri(baseUrl), "SHA1", hash);
    }

    private static bool IsHex(string value, int length) =>
        value.Length == length && Regex.IsMatch(value, "^[0-9a-fA-F]+$");

    private static bool IsSafeJar(string s) =>
        s.EndsWith(".jar", StringComparison.OrdinalIgnoreCase) &&
        s == Path.GetFileName(s) && !s.Contains("..") &&
        !s.Contains('/') && !s.Contains('\\') && s.Length < 200;

    private static async Task InstallJarAsync(DownloadFile item, string destination)
    {
        var cache = Path.Combine(Root, ".cache");
        Directory.CreateDirectory(cache);
        var cached = Path.Combine(cache, item.FileName);
        if (File.Exists(cached) && await VerifyAsync(cached, item))
        {
            File.Copy(cached, destination);
            return;
        }
        var temp = cached + "." + Guid.NewGuid().ToString("N") + ".part";
        try
        {
            using var response = await Client.GetAsync(item.Url, HttpCompletionOption.ResponseHeadersRead);
            response.EnsureSuccessStatusCode();
            if (response.Content.Headers.ContentLength is > 200_000_000)
                throw new IOException("JAR превышает ограничение размера.");
            await using (var input = await response.Content.ReadAsStreamAsync())
            await using (var output = File.Create(temp))
            {
                var buffer = new byte[128 * 1024];
                long total = 0;
                int read;
                while ((read = await input.ReadAsync(buffer)) > 0)
                {
                    total += read;
                    if (total > 200_000_000)
                        throw new IOException("JAR превышает ограничение размера.");
                    await output.WriteAsync(buffer.AsMemory(0, read));
                }
            }
            if (!await VerifyAsync(temp, item))
                throw new InvalidDataException("Хеш или размер не совпадает: " + item.Name);
            File.Move(temp, cached, true);
            File.Copy(cached, destination);
        }
        finally
        {
            if (File.Exists(temp)) File.Delete(temp);
        }
    }

    private static async Task<bool> VerifyAsync(string path, DownloadFile file)
    {
        using var stream = File.OpenRead(path);
        if (file.ExpectedBytes != 0 && stream.Length != file.ExpectedBytes) return false;
        using HashAlgorithm algo = file.Algorithm switch {
            "SHA512" => SHA512.Create(), "SHA256" => SHA256.Create(), "SHA1" => SHA1.Create(),
            _ => throw new InvalidDataException("Unsupported checksum type")
        };
        var value = Convert.ToHexString(await algo.ComputeHashAsync(stream));
        return string.Equals(value, file.Checksum, StringComparison.OrdinalIgnoreCase);
    }
}
