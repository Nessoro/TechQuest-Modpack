using System.Net;
using System.Security.Cryptography;
using System.Text.Json;

namespace TechQuestInstaller;

internal sealed record BootstrapFile(string Path, string Url, long Size, string Hash, bool Sha512);
internal sealed record BootstrapPlan(BootstrapFile Installer, IReadOnlyList<BootstrapFile> Libraries);

// No WinForms or game code: the exact GUI download path is also exercised by tests.
internal sealed class NeoForgeBootstrap(HttpClient client, Action<string> report)
{
    private readonly HashSet<string> unavailableHosts = new(StringComparer.OrdinalIgnoreCase);

    internal static BootstrapPlan ReadPlan(Stream stream)
    {
        using var document = JsonDocument.Parse(stream);
        var root = document.RootElement;
        if (root.GetProperty("minecraft").GetString() != "1.21.1" ||
            root.GetProperty("neoforge").GetString() != "21.1.264")
            throw new InvalidDataException("Неподдерживаемая версия плана NeoForge.");
        BootstrapFile ReadFile(JsonElement item, bool installer)
        {
            string path = item.GetProperty("path").GetString()!;
            string url = item.GetProperty("url").GetString()!;
            string hash = item.GetProperty(installer ? "sha512" : "sha1").GetString()!;
            long size = item.GetProperty("size").GetInt64();
            if (string.IsNullOrWhiteSpace(path) || path.Split('/').Any(p => p is "" or "." or "..") ||
                path.Contains('\\') || path.Contains(':') || Path.IsPathRooted(path) ||
                !Uri.TryCreate(url, UriKind.Absolute, out var uri) || uri.Scheme != "https" ||
                uri.Host is not ("maven.neoforged.net" or "libraries.minecraft.net") ||
                size <= 0 || size > 64 * 1024 * 1024 || hash.Length != (installer ? 128 : 40) ||
                !hash.All(Uri.IsHexDigit))
                throw new InvalidDataException("Неверные закреплённые метаданные NeoForge: " + path);
            return new(path, url, size, hash, installer);
        }
        var libraries = root.GetProperty("libraries").EnumerateArray().Select(e => ReadFile(e, false)).ToArray();
        if (libraries.Select(f => f.Path).Distinct(StringComparer.OrdinalIgnoreCase).Count() != libraries.Length)
            throw new InvalidDataException("Повторяющиеся пути библиотек NeoForge.");
        return new(ReadFile(root.GetProperty("installer"), true), libraries);
    }

    internal static IEnumerable<Uri> Sources(BootstrapFile file)
    {
        yield return new Uri(file.Url);
        yield return new Uri("https://maven.creeperhost.net/" + file.Path);
        if (new Uri(file.Url).Host == "libraries.minecraft.net")
        {
            yield return new Uri("https://maven.neoforged.net/releases/" + file.Path);
            yield return new Uri("https://repo.maven.apache.org/maven2/" + file.Path);
        }
        // Mirrors are transports only. Hashes always come from the pinned official installer.
        yield return new Uri("https://mirror.nju.edu.cn/bmclapi/" + file.Path);
        yield return new Uri("https://bmclapi2.bangbang93.com/maven/" + file.Path);
        if (file.Sha512)
            yield return new Uri("https://bmclapi2.bangbang93.com/neoforge/version/21.1.264/download/installer.jar");
    }

    private static bool Matches(byte[] bytes, BootstrapFile file) =>
        bytes.LongLength == file.Size && Convert.ToHexString(file.Sha512 ? SHA512.HashData(bytes) : SHA1.HashData(bytes))
            .Equals(file.Hash, StringComparison.OrdinalIgnoreCase);

    private async Task<byte[]> DownloadAsync(BootstrapFile file, CancellationToken token)
    {
        var failures = new List<string>();
        foreach (var source in Sources(file))
        {
            token.ThrowIfCancellationRequested();
            if (unavailableHosts.Contains(source.Host)) continue;
            report("Загрузка " + Path.GetFileName(file.Path) + " — " + source.Host);
            using var timeout = CancellationTokenSource.CreateLinkedTokenSource(token);
            timeout.CancelAfter(TimeSpan.FromSeconds(30));
            try
            {
                using var response = await client.GetAsync(source, HttpCompletionOption.ResponseHeadersRead, timeout.Token);
                response.EnsureSuccessStatusCode();
                if (response.Content.Headers.ContentLength is long length && length != file.Size)
                    throw new InvalidDataException("Неверный размер");
                await using var input = await response.Content.ReadAsStreamAsync(timeout.Token);
                using var output = new MemoryStream();
                byte[] buffer = new byte[81920];
                int read;
                while ((read = await input.ReadAsync(buffer, timeout.Token)) != 0)
                {
                    if (output.Length + read > file.Size) throw new InvalidDataException("Превышен размер файла");
                    output.Write(buffer, 0, read);
                }
                byte[] bytes = output.ToArray();
                if (!Matches(bytes, file)) throw new InvalidDataException("Размер или контрольная сумма не совпали");
                return bytes;
            }
            catch (OperationCanceledException) when (!token.IsCancellationRequested)
            {
                unavailableHosts.Add(source.Host);
                failures.Add(source.Host + ": тайм-аут 30 секунд");
            }
            catch (HttpRequestException ex)
            {
                if (ex.StatusCode is null or HttpStatusCode.Forbidden) unavailableHosts.Add(source.Host);
                failures.Add(source.Host + ": " + (ex.StatusCode?.ToString() ?? "ошибка соединения"));
            }
            catch (InvalidDataException ex) { failures.Add(source.Host + ": " + ex.Message); }
            catch (IOException ex)
            {
                unavailableHosts.Add(source.Host);
                failures.Add(source.Host + ": ошибка передачи: " + ex.Message);
            }
        }
        throw new IOException("Не удалось получить проверенный файл:\n" + file.Path + "\n" +
            string.Join("\n", failures.DefaultIfEmpty("Источники недоступны после предыдущего тайм-аута.")) +
            "\nПроверьте доступ к указанным источникам и повторите кнопку установки. " +
            "Уже проверенные файлы будут использованы повторно; запуск непроверенного JAR отменён.");
    }

    internal async Task<string> PrepareAsync(BootstrapPlan plan, string launcherRoot, string cacheRoot,
        CancellationToken token)
    {
        // The user selects the official launcher's root, never the modpack's game directory.
        if (!File.Exists(Path.Combine(launcherRoot, "versions", "1.21.1", "1.21.1.json")) ||
            !File.Exists(Path.Combine(launcherRoot, "versions", "1.21.1", "1.21.1.jar")))
            throw new IOException("В выбранной папке Launcher нет установленной Minecraft 1.21.1. " +
                "Откройте официальный Minecraft Launcher, установите и запустите обычную 1.21.1 один раз, " +
                "закройте игру и повторите установку NeoForge. Папка модпака выбирается позднее как Game Directory.");
        async Task EnsureAsync(BootstrapFile file, string destination, bool preserveExisting)
        {
            token.ThrowIfCancellationRequested();
            if (File.Exists(destination))
            {
                if (Matches(await File.ReadAllBytesAsync(destination, token), file)) return;
                if (preserveExisting)
                    throw new IOException("Существующая библиотека отличается от официальной и не перезаписана:\n" +
                        destination + "\nСохраните резервную копию этого файла и проверьте установку Minecraft в Launcher.");
            }
            byte[] bytes = await DownloadAsync(file, token);
            Directory.CreateDirectory(Path.GetDirectoryName(destination)!);
            string temporary = destination + ".techquest-" + Guid.NewGuid().ToString("N");
            try
            {
                await File.WriteAllBytesAsync(temporary, bytes, token);
                token.ThrowIfCancellationRequested();
                File.Move(temporary, destination, overwrite: !preserveExisting);
            }
            finally { if (File.Exists(temporary)) File.Delete(temporary); }
        }
        string installer = Path.Combine(cacheRoot, "neoforge-21.1.264-installer.jar");
        await EnsureAsync(plan.Installer, installer, false);
        int index = 0;
        foreach (var file in plan.Libraries)
        {
            report($"Подготовка библиотеки {++index}/{plan.Libraries.Count}: {Path.GetFileName(file.Path)}");
            await EnsureAsync(file, Path.Combine(launcherRoot, "libraries", file.Path.Replace('/', Path.DirectorySeparatorChar)), true);
        }
        report("Установщик и библиотеки NeoForge проверены. Открывается официальное окно Install client.");
        return installer;
    }
}
