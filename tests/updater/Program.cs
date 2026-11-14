using System.IO.Compression;
using System.Security;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using TechQuestInstaller;

static void Assert(bool test, string message)
{
    if (!test) throw new Exception("Updater test failed: " + message);
}
static ManagedMod Identity(string name, byte[] bytes) =>
    new(name, Convert.ToHexString(SHA512.HashData(bytes)).ToLowerInvariant(), bytes.Length);

static MemoryStream FakePack(params (ManagedMod identity, byte[] contents)[] mods)
{
    var stream = new MemoryStream();
    using (var zip = new ZipArchive(stream, ZipArchiveMode.Create, leaveOpen: true))
    {
        var index = new
        {
            game = "minecraft",
            versionId = "0.3.3-alpha",
            dependencies = new Dictionary<string, string> {
                ["minecraft"] = "1.21.1", ["neoforge"] = "21.1.264"
            },
            files = mods.Select(x => new
            {
                path = "mods/" + x.identity.Name,
                fileSize = x.identity.Size,
                hashes = new { sha512 = x.identity.Sha512,
                    sha1 = Convert.ToHexString(SHA1.HashData(x.contents)).ToLowerInvariant() },
                env = new { client = "required", server = "required" },
                downloads = new[] { "https://cdn.modrinth.com/data/test/fake.jar" }
            }).ToArray()
        };
        using var writer = new StreamWriter(zip.CreateEntry("modrinth.index.json").Open(), new UTF8Encoding(false));
        writer.Write(JsonSerializer.Serialize(index));
    }
    stream.Position = 0;
    return stream;
}

// Signature verifier rejects tampering without installing anything.
using (var rsa = RSA.Create(3072))
{
    byte[] payload = Encoding.UTF8.GetBytes("release manifest");
    string publicKey = rsa.ExportRSAPublicKeyPem();
    byte[] sig = rsa.SignData(payload, HashAlgorithmName.SHA256, RSASignaturePadding.Pkcs1);
    ReleaseUpdates.VerifySignature(payload, sig, publicKey);
    payload[0] ^= 1;
    bool rejected = false;
    try { ReleaseUpdates.VerifySignature(payload, sig, publicKey); }
    catch (SecurityException) { rejected = true; }
    Assert(rejected, "tampered release signature must fail closed");
}

string root = Path.Combine(Path.GetTempPath(), "techquest-update-test-" + Guid.NewGuid().ToString("N"));
Directory.CreateDirectory(root);
try
{
    string mods = Path.Combine(root, "mods");
    Directory.CreateDirectory(mods);
    Directory.CreateDirectory(Path.Combine(root, "saves", "my-world"));
    Directory.CreateDirectory(Path.Combine(root, "config"));
    File.WriteAllText(Path.Combine(root, "saves", "my-world", "level.dat"), "player-world");
    File.WriteAllText(Path.Combine(root, "config", "user.toml"), "private-user-settings");
    File.WriteAllText(Path.Combine(root, "options.txt"), "private-user-options");
    File.WriteAllText(Path.Combine(mods, "manual.jar"), "user-installed-mod");

    var oldBytes = Encoding.UTF8.GetBytes("old-mod-bytes");
    var sameBytes = Encoding.UTF8.GetBytes("unchanged-mod");
    var newBytes = Encoding.UTF8.GetBytes("replacement-mod");
    var old = Identity("old.jar", oldBytes);
    var same = Identity("same.jar", sameBytes);
    var next = Identity("next.jar", newBytes);
    File.WriteAllBytes(Path.Combine(mods, old.Name), oldBytes);
    File.WriteAllBytes(Path.Combine(mods, same.Name), sameBytes);
    using (var pack = FakePack((old, oldBytes), (same, sameBytes)))
        TransactionalMods.RecordInitialInstallation(root, pack);

    var start = TransactionalMods.GetInstalled(root)!;
    Assert(start.Mods.Count == 2, "initial managed state");
    Assert(!start.Mods.Any(x => x.Name == "manual.jar"), "unmanaged mod is not tracked");

    var desired = new PackState { ReleaseTag = "v0.3.3-micro3-preview", Mods = new() { same, next } };
    bool failed = false;
    try
    {
        await TransactionalMods.ApplyForTestsAsync(root, desired,
            (item, path, ct) => throw new IOException("controlled download failure"),
            CancellationToken.None);
    }
    catch (IOException) { failed = true; }
    Assert(failed, "download failure was exercised");
    Assert(File.Exists(Path.Combine(mods, "old.jar")), "old mod survives staged download failure");
    Assert(TransactionalMods.GetInstalled(root)!.ReleaseTag == start.ReleaseTag,
        "failed update has no state mutation");

    int changed = await TransactionalMods.ApplyForTestsAsync(root, desired,
        (item, path, ct) =>
        {
            if (item.Name != next.Name) throw new Exception("unexpected download");
            File.WriteAllBytes(path, newBytes);
            return Task.CompletedTask;
        }, CancellationToken.None);
    Assert(changed == 1, "only one changed mod downloaded");
    Assert(!File.Exists(Path.Combine(mods, "old.jar")), "retired managed mod removed");
    Assert(File.ReadAllBytes(Path.Combine(mods, "next.jar")).SequenceEqual(newBytes),
        "new managed mod installed");
    Assert(TransactionalMods.GetInstalled(root)!.ReleaseTag == desired.ReleaseTag,
        "state advanced after successful transaction");

    int restored = await TransactionalMods.RollbackAsync(root, null, CancellationToken.None);
    Assert(restored == 1, "rollback restored old mod");
    Assert(File.ReadAllBytes(Path.Combine(mods, "old.jar")).SequenceEqual(oldBytes),
        "old bytes restored");
    Assert(!File.Exists(Path.Combine(mods, "next.jar")), "new managed mod removed by rollback");
    Assert(TransactionalMods.GetInstalled(root)!.ReleaseTag == start.ReleaseTag,
        "rollback state restored");

    // Simulate a hard crash after journal creation and partial deletion.
    string stateDir = Path.Combine(root, ".techquest");
    string id = "backup-" + Guid.NewGuid().ToString("N");
    string backup = Path.Combine(stateDir, "backups", id);
    Directory.CreateDirectory(backup);
    File.Copy(Path.Combine(mods, "old.jar"), Path.Combine(backup, "old.jar"));
    File.WriteAllText(Path.Combine(stateDir, "transaction.json"),
        JsonSerializer.Serialize(new PendingTransaction
        {
            Previous = start, Desired = desired, BackupId = id
        }));
    File.Delete(Path.Combine(mods, "old.jar"));
    File.WriteAllBytes(Path.Combine(mods, "next.jar"), Encoding.UTF8.GetBytes("user-replaced-file"));
    bool unsafeRecoveryBlocked = false;
    try { TransactionalMods.RecoverPending(root); }
    catch (InvalidDataException) { unsafeRecoveryBlocked = true; }
    catch (SecurityException) { unsafeRecoveryBlocked = true; }
    Assert(unsafeRecoveryBlocked, "crash recovery refuses to delete unexpected user bytes");
    Assert(File.ReadAllText(Path.Combine(mods, "next.jar")) == "user-replaced-file",
        "unexpected user file preserved");
    File.WriteAllBytes(Path.Combine(mods, "next.jar"), newBytes);
    TransactionalMods.RecoverPending(root);
    Assert(File.Exists(Path.Combine(mods, "old.jar")), "journal recovery restored the mod");
    Assert(!File.Exists(Path.Combine(mods, "next.jar")), "journal recovery removed partial update");
    Assert(!File.Exists(Path.Combine(stateDir, "transaction.json")), "journal cleared after recovery");

    Assert(File.ReadAllText(Path.Combine(root, "saves", "my-world", "level.dat")) == "player-world",
        "save data preserved");
    Assert(File.ReadAllText(Path.Combine(root, "config", "user.toml")) == "private-user-settings",
        "user config preserved");
    Assert(File.ReadAllText(Path.Combine(root, "options.txt")) == "private-user-options",
        "player options preserved");
    Assert(File.ReadAllText(Path.Combine(mods, "manual.jar")) == "user-installed-mod",
        "unmanaged local mods preserved");

    // The first-party techquest-compat JAR is inside mrpack overrides, not its download list.
    using (var compatPack = FakePack((old, oldBytes)))
    {
        using (var zip = new ZipArchive(compatPack, ZipArchiveMode.Update, leaveOpen: true))
        {
            using var outStream = zip.CreateEntry("overrides/mods/techquest-compat-1.0.0.jar").Open();
            outStream.Write(Encoding.UTF8.GetBytes("trusted-compat-fixture"));
        }
        compatPack.Position = 0;
        var unpacked = ReleaseUpdates.ParsePack(compatPack);
        Assert(unpacked.BundledMods.Count == 1 &&
               unpacked.BundledMods[0].Identity.Name == "techquest-compat-1.0.0.jar",
               "first-party bundled compatibility JAR is tracked");
    }

    using (var malformed = new MemoryStream())
    {
        using (var zip = new ZipArchive(malformed, ZipArchiveMode.Create, leaveOpen: true))
        {
            using var writer = new StreamWriter(zip.CreateEntry("modrinth.index.json").Open());
            writer.Write("""
                {"game":"minecraft","versionId":"0.3.3-alpha",
                "dependencies":{"minecraft":"1.21.1","neoforge":"21.1.264"},
                "files":[{"path":"mods/../../steal.jar","fileSize":10,
                "env":{"client":"required"},"hashes":{"sha512":"aaa"},
                "downloads":["https://evil.example/steal.jar"]}]}
                """);
        }
        malformed.Position = 0;
        bool blocked = false;
        try { ReleaseUpdates.ParsePack(malformed); }
        catch (SecurityException) { blocked = true; }
        Assert(blocked, "pack path traversal rejected");
    }

    Console.WriteLine("Updater tests passed: signature, differential update, failure, rollback, crash recovery, player data and paths.");
}
finally
{
    Directory.Delete(root, recursive: true);
}
