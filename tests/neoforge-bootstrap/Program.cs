using System.Net;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using TechQuestInstaller;

static void Check(bool condition, string message)
{
    if (!condition) throw new Exception(message);
}
static string Hash(byte[] bytes, bool strong) => Convert.ToHexString(strong ? SHA512.HashData(bytes) : SHA1.HashData(bytes));
static void VanillaFixture(string root)
{
    Directory.CreateDirectory(Path.Combine(root, "versions", "1.21.1"));
    File.WriteAllText(Path.Combine(root, "versions", "1.21.1", "1.21.1.json"), "{\"id\":\"1.21.1\"}");
    File.WriteAllBytes(Path.Combine(root, "versions", "1.21.1", "1.21.1.jar"), [1]);
}

using var resource = Assembly.GetExecutingAssembly().GetManifestResourceStream("TechQuest.NeoForge.bootstrap.json")!;
BootstrapPlan actual = NeoForgeBootstrap.ReadPlan(resource);
Check(actual.Libraries.Count == 70, "Expected the pinned 70-library official plan");
string temporary = Path.Combine(Path.GetTempPath(), "TechQuest-bootstrap-tests-" + Guid.NewGuid().ToString("N"));
Directory.CreateDirectory(temporary);
try
{
    if (args.Length == 1 && args[0].StartsWith("--probe-"))
    {
        bool outage = args[0] == "--probe-maven-outage";
        Check(outage || args[0] == "--probe-primary", "Unknown probe mode");
        using var client = new HttpClient(new OutageHandler(outage)) { Timeout = Timeout.InfiniteTimeSpan };
        string root = Path.Combine(temporary, "fixture-launcher");
        VanillaFixture(root); // Only downloader integration. No Minecraft/NeoForge code is run.
        string installer = await new NeoForgeBootstrap(client, Console.WriteLine).PrepareAsync(actual, root,
            Path.Combine(temporary, "cache"), CancellationToken.None);
        Check(File.Exists(installer), "Verified installer missing");
        Check(actual.Libraries.All(f => File.Exists(Path.Combine(root, "libraries", f.Path))), "Libraries missing");
        Console.WriteLine($"PASS: verified installer + 70 libraries; simulated Maven outage={outage}; game not run");
        return;
    }

    byte[] jar = Encoding.UTF8.GetBytes("fixture-installer");
    byte[] library = Encoding.UTF8.GetBytes("fixture-library");
    BootstrapPlan fixture = new(new("org/test/installer.jar", "https://maven.neoforged.net/releases/org/test/installer.jar",
        jar.Length, Hash(jar, true), true), [new("org/test/library.jar", "https://maven.neoforged.net/releases/org/test/library.jar",
        library.Length, Hash(library, false), false)]);
    using var handler = new FixtureHandler(jar, library);
    using var fake = new HttpClient(handler);
    string launcher = Path.Combine(temporary, "launcher");
    VanillaFixture(launcher);
    string cache = Path.Combine(temporary, "cache");
    await new NeoForgeBootstrap(fake, _ => { }).PrepareAsync(fixture, launcher, cache, CancellationToken.None);
    Check(handler.PrimaryRequests == 1, "A failed origin should be skipped for subsequent libraries");
    Check(handler.MirrorRequests == 2, "Installer and library must both use verified fallback");
    int requests = handler.MirrorRequests;
    await new NeoForgeBootstrap(fake, _ => { }).PrepareAsync(fixture, launcher, cache, CancellationToken.None);
    Check(handler.MirrorRequests == requests, "Verified cache must work without another download");

    string target = Path.Combine(launcher, "libraries", fixture.Libraries[0].Path);
    File.WriteAllText(target, "user-data");
    try
    {
        await new NeoForgeBootstrap(fake, _ => { }).PrepareAsync(fixture, launcher, cache, CancellationToken.None);
        throw new Exception("Modified existing file was accepted");
    }
    catch (IOException) { Check(File.ReadAllText(target) == "user-data", "Existing data overwritten"); }

    handler.Corrupt = true;
    string corruptRoot = Path.Combine(temporary, "corrupt-launcher");
    VanillaFixture(corruptRoot);
    try
    {
        await new NeoForgeBootstrap(fake, _ => { }).PrepareAsync(fixture, corruptRoot,
            Path.Combine(temporary, "bad-cache"), CancellationToken.None);
        throw new Exception("Hash mismatch was accepted");
    }
    catch (IOException ex) { Check(ex.Message.Contains("installer.jar"), "Diagnostic must identify failed file"); }
    Check(!Directory.Exists(Path.Combine(corruptRoot, "libraries")), "Corrupt payload was installed");

    using var cancelled = new CancellationTokenSource();
    cancelled.Cancel();
    try
    {
        await new NeoForgeBootstrap(fake, _ => { }).PrepareAsync(fixture, launcher, cache, cancelled.Token);
        throw new Exception("Cancellation was ignored");
    }
    catch (OperationCanceledException) { }
    Console.WriteLine("PASS: fallback for installer/libraries, failed-host circuit, cache, integrity rejection, preservation, cancellation");
}
finally { Directory.Delete(temporary, true); }

sealed class FixtureHandler(byte[] installer, byte[] library) : HttpMessageHandler
{
    public int PrimaryRequests;
    public int MirrorRequests;
    public bool Corrupt;
    protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken token)
    {
        if (request.RequestUri!.Host == "maven.neoforged.net")
        {
            PrimaryRequests++;
            throw new HttpRequestException("Simulated unreachable Maven");
        }
        MirrorRequests++;
        byte[] bytes = request.RequestUri.AbsolutePath.Contains("installer") ? installer : library;
        return Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK) {
            Content = new ByteArrayContent(Corrupt ? new byte[bytes.Length] : bytes)
        });
    }
}

sealed class OutageHandler(bool outage) : DelegatingHandler(new HttpClientHandler())
{
    protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken token)
    {
        if (outage && request.RequestUri!.Host == "maven.neoforged.net")
            throw new HttpRequestException("Intentionally unavailable Maven for fallback integration test");
        return base.SendAsync(request, token);
    }
}
