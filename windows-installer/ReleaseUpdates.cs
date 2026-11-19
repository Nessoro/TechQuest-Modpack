using System.IO.Compression;
using System.Net;
using System.Security;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace TechQuestInstaller;

// Release signatures are verified against a public key embedded in the EXE.
// No passwords, Minecraft session data, browser profiles, cookies or access tokens are read.
internal sealed record TrustedRelease(
    string Tag, string VersionId, string PackHash, string InstallerHash,
    Uri PackUrl, Uri InstallerUrl);

internal sealed record ManagedMod(string Name, string Sha512, long Size);
internal sealed record DownloadMod(ManagedMod Identity, Uri Url, string? Sha1);
internal sealed record BundledMod(ManagedMod Identity, byte[] Bytes);
internal sealed record ReleasePack(
    string VersionId, List<DownloadMod> Mods, List<BundledMod> BundledMods);

internal static class ReleaseUpdates
{
    private const string Repo = "Nessoro/TechQuest-Modpack";
    private const string ReleasesApi = "https://api.github.com/repos/Nessoro/TechQuest-Modpack/releases?per_page=20";
    private const string KeyResource = "TechQuest.Update.PublicKey.pem";
    private static readonly HttpClient Client = CreateClient();

    private static HttpClient CreateClient()
    {
        var client = new HttpClient(new HttpClientHandler
        {
            UseCookies = false,
            UseDefaultCredentials = false,
            AllowAutoRedirect = false
        }) { Timeout = TimeSpan.FromMinutes(5) };
        client.DefaultRequestHeaders.UserAgent.ParseAdd("TechQuest-Installer/0.3.3");
        return client;
    }

    private static bool SafeHost(Uri url, bool modDownload)
    {
        if (url.Scheme != Uri.UriSchemeHttps || url.UserInfo.Length > 0)
            return false;
        string host = url.DnsSafeHost.ToLowerInvariant();
        if (host is "api.github.com" or "github.com" or "release-assets.githubusercontent.com"
            or "objects.githubusercontent.com")
            return true;
        return modDownload && (host is "cdn.modrinth.com" or "raw.githubusercontent.com");
    }

    private static async Task<HttpResponseMessage> OpenAsync(
        Uri url, bool modDownload, CancellationToken cancellation)
    {
        for (int redirects = 0; redirects <= 5; redirects++)
        {
            if (!SafeHost(url, modDownload)) throw new SecurityException("Blocked download host: " + url.Host);
            using var request = new HttpRequestMessage(HttpMethod.Get, url);
            var response = await Client.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, cancellation);
            if ((int)response.StatusCode is 301 or 302 or 303 or 307 or 308)
            {
                Uri? next = response.Headers.Location;
                response.Dispose();
                if (next is null) throw new HttpRequestException("Redirect without Location");
                url = next.IsAbsoluteUri ? next : new Uri(url, next);
                continue;
            }
            response.EnsureSuccessStatusCode();
            return response;
        }
        throw new SecurityException("Too many download redirects");
    }

    internal static async Task<byte[]> GetLimitedAsync(Uri url, int maxBytes, CancellationToken token)
    {
        using var response = await OpenAsync(url, false, token);
        if (response.Content.Headers.ContentLength > maxBytes)
            throw new InvalidDataException("Remote metadata is too large.");
        await using var input = await response.Content.ReadAsStreamAsync(token);
        using var output = new MemoryStream();
        byte[] buffer = new byte[32768];
        int read;
        while ((read = await input.ReadAsync(buffer, token)) != 0)
        {
            if (output.Length + read > maxBytes) throw new InvalidDataException("Remote metadata size exceeded.");
            output.Write(buffer, 0, read);
        }
        return output.ToArray();
    }

    internal static async Task DownloadCheckedAsync(
        Uri url, string destination, ManagedMod expected, string? sha1, CancellationToken token)
    {
        if (!SafeHost(url, true)) throw new SecurityException("Mod download source not allowed");
        using var response = await OpenAsync(url, true, token);
        if (response.Content.Headers.ContentLength > expected.Size)
            throw new InvalidDataException("Unexpected download size");
        await using (var source = await response.Content.ReadAsStreamAsync(token))
        await using (var dest = new FileStream(destination, FileMode.CreateNew, FileAccess.Write, FileShare.None))
        {
            byte[] buffer = new byte[65536];
            long written = 0;
            int count;
            while ((count = await source.ReadAsync(buffer, token)) > 0)
            {
                written += count;
                if (written > expected.Size) throw new InvalidDataException("Download exceeds manifest size");
                await dest.WriteAsync(buffer.AsMemory(0, count), token);
            }
            if (written != expected.Size) throw new InvalidDataException("Truncated mod download");
        }
        VerifyFile(destination, expected, sha1);
    }

    internal static void VerifyFile(string path, ManagedMod mod, string? sha1 = null)
    {
        if (!File.Exists(path) || (File.GetAttributes(path) & FileAttributes.ReparsePoint) != 0)
            throw new SecurityException("Missing or redirected managed mod: " + mod.Name);
        var file = new FileInfo(path);
        if (file.Length != mod.Size) throw new InvalidDataException("Modified managed mod: " + mod.Name);
        using var stream = File.OpenRead(path);
        if (!SHA512.HashData(stream).AsSpan().SequenceEqual(Convert.FromHexString(mod.Sha512)))
            throw new InvalidDataException("SHA-512 mismatch: " + mod.Name);
        if (sha1 != null)
        {
            stream.Position = 0;
            if (!SHA1.HashData(stream).AsSpan().SequenceEqual(Convert.FromHexString(sha1)))
                throw new InvalidDataException("SHA-1 mismatch: " + mod.Name);
        }
    }

    private static bool IsHash(string? value, int length) =>
        value is not null && value.Length == length &&
        value.All(c => (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F'));

    private static bool SafeName(string value) =>
        value.Length is > 0 and <= 180 &&
        value == Path.GetFileName(value) &&
        value.IndexOfAny(Path.GetInvalidFileNameChars()) < 0 &&
        !value.Contains("..", StringComparison.Ordinal) &&
        !value.Contains('\\') &&
        !value.Contains('/') &&
        value.EndsWith(".jar", StringComparison.OrdinalIgnoreCase) &&
        value.All(c => c is >= ' ' and <= '~' || c > 127);

    private static Uri Asset(JsonElement release, string name, string tag)
    {
        foreach (var asset in release.GetProperty("assets").EnumerateArray())
        {
            if (asset.GetProperty("name").GetString() != name) continue;
            string? url = asset.GetProperty("browser_download_url").GetString();
            string expected = "https://github.com/" + Repo + "/releases/download/" + tag + "/" + name;
            if (!string.Equals(url, expected, StringComparison.Ordinal))
                throw new SecurityException("Unexpected release asset location");
            return new Uri(expected);
        }
        throw new FileNotFoundException("Signed release asset missing: " + name);
    }

    private static string ReadPublicKey()
    {
        using var stream = typeof(ReleaseUpdates).Assembly.GetManifestResourceStream(KeyResource)
            ?? throw new SecurityException("Updater public key is missing from the installer.");
        using var reader = new StreamReader(stream, Encoding.ASCII);
        return reader.ReadToEnd();
    }

    internal static void VerifySignature(byte[] content, byte[] signature, string publicKeyPem)
    {
        using var rsa = RSA.Create();
        rsa.ImportFromPem(publicKeyPem);
        if (!rsa.VerifyData(content, signature, HashAlgorithmName.SHA256, RSASignaturePadding.Pkcs1))
            throw new SecurityException("Update signature is invalid. No update will be installed.");
    }

    internal static async Task<TrustedRelease?> CheckAsync(bool includePreview, CancellationToken token)
    {
        byte[] releases = await GetLimitedAsync(new Uri(ReleasesApi), 512 * 1024, token);
        using var doc = JsonDocument.Parse(releases);
        foreach (var release in doc.RootElement.EnumerateArray())
        {
            if (release.GetProperty("draft").GetBoolean() ||
                (!includePreview && release.GetProperty("prerelease").GetBoolean()))
                continue;
            string tag = release.GetProperty("tag_name").GetString() ?? "";
            if (!Regex.IsMatch(tag, @"^v[0-9A-Za-z][0-9A-Za-z._-]{0,79}$", RegexOptions.CultureInvariant))
                continue;
            var names = release.GetProperty("assets").EnumerateArray()
                .Select(x => x.GetProperty("name").GetString()).ToHashSet(StringComparer.Ordinal);
            if (!names.Contains("techquest-release.json") || !names.Contains("techquest-release.sig"))
                continue; // Legacy releases cannot update the launcher.
            Uri manifestUrl = Asset(release, "techquest-release.json", tag);
            Uri signatureUrl = Asset(release, "techquest-release.sig", tag);
            byte[] bytes = await GetLimitedAsync(manifestUrl, 16 * 1024, token);
            byte[] signatureText = await GetLimitedAsync(signatureUrl, 16 * 1024, token);
            byte[] signature = Convert.FromBase64String(Encoding.ASCII.GetString(signatureText).Trim());
            VerifySignature(bytes, signature, ReadPublicKey());
            using var signedDoc = JsonDocument.Parse(bytes);
            var data = signedDoc.RootElement;
            if (data.GetProperty("schema").GetInt32() != 1 ||
                data.GetProperty("repository").GetString() != Repo ||
                data.GetProperty("tag").GetString() != tag)
                throw new SecurityException("Signed release identity mismatch");
            string version = data.GetProperty("versionId").GetString() ?? "";
            string packHash = data.GetProperty("packSha256").GetString() ?? "";
            string exeHash = data.GetProperty("installerSha256").GetString() ?? "";
            if (version.Length is < 3 or > 80 || !IsHash(packHash, 64) || !IsHash(exeHash, 64))
                throw new SecurityException("Invalid signed release metadata");
            return new TrustedRelease(tag, version, packHash, exeHash,
                Asset(release, "TechQuest_Optimized.mrpack", tag),
                Asset(release, "TechQuestInstaller.exe", tag));
        }
        return null;
    }

    internal static async Task<byte[]> DownloadPackAsync(TrustedRelease release, CancellationToken token)
    {
        byte[] bytes = await GetLimitedAsync(release.PackUrl, 64 * 1024 * 1024, token);
        if (!SHA256.HashData(bytes).AsSpan().SequenceEqual(Convert.FromHexString(release.PackHash)))
            throw new SecurityException("Signed pack SHA-256 mismatch");
        return bytes;
    }

    internal static ReleasePack ParsePack(Stream contents)
    {
        using var archive = new ZipArchive(contents, ZipArchiveMode.Read, leaveOpen: true);
        var entry = archive.GetEntry("modrinth.index.json")
            ?? throw new InvalidDataException("Missing modrinth.index.json");
        if (entry.Length > 16 * 1024 * 1024) throw new InvalidDataException("Pack index too large");
        using var stream = entry.Open();
        using var doc = JsonDocument.Parse(stream);
        var root = doc.RootElement;
        var deps = root.GetProperty("dependencies");
        if (root.GetProperty("game").GetString() != "minecraft" ||
            deps.GetProperty("minecraft").GetString() != "1.21.1" ||
            deps.GetProperty("neoforge").GetString() != "21.1.264")
            throw new SecurityException("Unexpected Minecraft/NeoForge version");
        string version = root.GetProperty("versionId").GetString() ?? "";
        var mods = new List<DownloadMod>();
        var unique = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var file in root.GetProperty("files").EnumerateArray())
        {
            if (file.GetProperty("env").TryGetProperty("client", out var side) &&
                side.GetString() == "unsupported") continue;
            string path = file.GetProperty("path").GetString() ?? "";
            if (!path.StartsWith("mods/", StringComparison.Ordinal) || !SafeName(path[5..]) ||
                !unique.Add(path[5..]))
                throw new SecurityException("Unsafe or duplicate mod path");
            var hash = file.GetProperty("hashes");
            string sha512 = hash.GetProperty("sha512").GetString() ?? "";
            string? sha1 = hash.TryGetProperty("sha1", out var one) ? one.GetString() : null;
            long size = file.GetProperty("fileSize").GetInt64();
            if (!IsHash(sha512, 128) || (sha1 != null && !IsHash(sha1, 40)) ||
                size is <= 0 or > 536870912)
                throw new SecurityException("Invalid mod hashes/size");
            string? url = file.GetProperty("downloads").EnumerateArray().FirstOrDefault().GetString();
            if (!Uri.TryCreate(url, UriKind.Absolute, out var uri) ||
                !SafeHost(uri, true) ||
                (uri.Host == "github.com" &&
                 (uri.AbsolutePath != "/zentixua/incoming/releases/download/v3.10.4/incoming-3.10.4.jar" ||
                  uri.Query != "" || uri.Fragment != "")) ||
                (uri.Host == "raw.githubusercontent.com" &&
                 !uri.AbsolutePath.StartsWith("/Nessoro/TechQuest-Modpack/", StringComparison.Ordinal)))
                throw new SecurityException("Untrusted mod URL");
            mods.Add(new DownloadMod(new ManagedMod(path[5..], sha512.ToLowerInvariant(), size), uri, sha1));
        }
        var bundled = new List<BundledMod>();
        foreach (var embedded in archive.Entries)
        {
            if (!embedded.FullName.StartsWith("overrides/mods/", StringComparison.Ordinal))
                continue;
            string name = embedded.FullName["overrides/mods/".Length..];
            // Only our own compatibility JAR is automatically managed as an override.
            if (!Regex.IsMatch(name, @"^techquest-compat-[A-Za-z0-9._-]+\.jar$", RegexOptions.CultureInvariant) ||
                !SafeName(name) || !unique.Add(name) ||
                embedded.Length is <= 0 or > 16 * 1024 * 1024)
                throw new SecurityException("Invalid bundled TechQuest mod");
            using var bundledStream = embedded.Open();
            using var memory = new MemoryStream();
            bundledStream.CopyTo(memory);
            byte[] data = memory.ToArray();
            if (data.LongLength != embedded.Length)
                throw new InvalidDataException("Truncated bundled TechQuest JAR");
            bundled.Add(new BundledMod(
                new ManagedMod(name, Convert.ToHexString(SHA512.HashData(data)).ToLowerInvariant(),
                    data.LongLength), data));
        }
        if (mods.Count == 0 || mods.Count + bundled.Count > 1000)
            throw new InvalidDataException("Invalid mod count");
        return new ReleasePack(version, mods, bundled);
    }

    internal static async Task<string> DownloadInstallerAsync(
        TrustedRelease release, string baseDir, CancellationToken token)
    {
        string safeTag = release.Tag;
        if (!Regex.IsMatch(safeTag, @"^[A-Za-z0-9._-]+$")) throw new SecurityException("Unsafe release tag");
        string dir = Path.Combine(baseDir, "verified-updates");
        Directory.CreateDirectory(dir);
        if ((File.GetAttributes(dir) & FileAttributes.ReparsePoint) != 0)
            throw new SecurityException("Updater download directory is a redirect.");
        string dest = Path.Combine(dir, "TechQuestInstaller-" + safeTag + ".exe");
        string temp = Path.Combine(dir, Guid.NewGuid().ToString("N") + ".tmp");
        try
        {
            using var response = await OpenAsync(release.InstallerUrl, false, token);
            if (response.Content.Headers.ContentLength > 250 * 1024 * 1024)
                throw new InvalidDataException("Installer too large");
            await using (var source = await response.Content.ReadAsStreamAsync(token))
            await using (var target = new FileStream(temp, FileMode.CreateNew, FileAccess.Write, FileShare.None))
            {
                byte[] buffer = new byte[65536];
                int count;
                long size = 0;
                while ((count = await source.ReadAsync(buffer, token)) > 0)
                {
                    size += count;
                    if (size > 250 * 1024 * 1024) throw new InvalidDataException("Installer too large");
                    await target.WriteAsync(buffer.AsMemory(0, count), token);
                }
            }
            await using (var stream = File.OpenRead(temp))
                if (!SHA256.HashData(stream).AsSpan().SequenceEqual(Convert.FromHexString(release.InstallerHash)))
                    throw new SecurityException("Signed installer hash mismatch");
            if (File.Exists(dest) && (File.GetAttributes(dest) & FileAttributes.ReparsePoint) != 0)
                throw new SecurityException("Installer destination is a redirect");
            File.Move(temp, dest, true); // Never launch a downloaded executable automatically.
            return dest;
        }
        finally { if (File.Exists(temp)) File.Delete(temp); }
    }
}
