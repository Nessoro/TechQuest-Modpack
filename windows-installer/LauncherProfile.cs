using System.Diagnostics;
using System.Security;

namespace TechQuestInstaller;

internal sealed partial class InstallerForm
{
    private enum ProfileMode { New, Managed, Legacy, Unsafe }

    private ProfileMode currentProfile = ProfileMode.New;

    private void RefreshProfileStatus()
    {
        if (cancellation != null) return;
        try
        {
            string root = Path.GetFullPath(location.Text);
            var installed = TransactionalMods.GetInstalled(root);
            bool anyJar = Directory.Exists(Path.Combine(root, "mods")) &&
                Directory.EnumerateFiles(Path.Combine(root, "mods"), "*.jar",
                    SearchOption.TopDirectoryOnly).Any();
            currentProfile = installed != null ? ProfileMode.Managed
                : anyJar ? ProfileMode.Legacy : ProfileMode.New;
            install.Enabled = true;
            switch (currentProfile)
            {
                case ProfileMode.Managed:
                    profileBadge.Text = "Установлена TechQuest: " + installed!.ReleaseTag +
                                        " · " + installed.Mods.Count + " управляемых модов";
                    install.Text = "Проверить TechQuest";
                    playOfficial.Enabled = true;
                    verifyIntegrity.Enabled = true;
                    break;
                case ProfileMode.Legacy:
                    profileBadge.Text = "Обнаружены моды без данных лаунчера. Можно проверить и подключить.";
                    install.Text = "Подключить сборку";
                    playOfficial.Enabled = false;
                    verifyIntegrity.Enabled = false;
                    break;
                default:
                    profileBadge.Text = "TechQuest не установлен в выбранной папке";
                    install.Text = "Установить TechQuest";
                    playOfficial.Enabled = false;
                    verifyIntegrity.Enabled = false;
                    break;
            }
            rollback.Enabled = installed is not null &&
                File.Exists(Path.Combine(root, ".techquest", "rollback.json"));
            updateAvailable = availableRelease != null && installed != null &&
                installed.ReleaseTag != availableRelease.Tag;
            applyUpdate.Enabled = updateAvailable;
        }
        catch (Exception)
        {
            currentProfile = ProfileMode.Unsafe;
            profileBadge.Text = "Невозможно проверить папку. Выберите отдельную папку TechQuest.";
            install.Text = "Папка недоступна";
            install.Enabled = false;
            playOfficial.Enabled = false;
            verifyIntegrity.Enabled = false;
            rollback.Enabled = false;
            applyUpdate.Enabled = false;
        }
    }

    private async Task PrimaryActionAsync()
    {
        RefreshProfileStatus();
        switch (currentProfile)
        {
            case ProfileMode.New:
                await InstallAsync();
                break;
            case ProfileMode.Managed:
                await VerifyExistingAsync();
                break;
            case ProfileMode.Legacy:
                await AdoptLegacyAsync();
                break;
            default:
                MessageBox.Show(this, "Папка недоступна или содержит повреждённое состояние TechQuest.",
                    "Безопасная установка", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                break;
        }
    }

    private async Task AdoptLegacyAsync()
    {
        string root = Path.GetFullPath(location.Text);
        var answer = MessageBox.Show(this,
            "В этой папке уже есть моды. Проверить полный состав и хеши файлов " +
            "по встроенной версии TechQuest?\n\n" +
            "Если это действительно прежняя установка той же версии, она будет подключена " +
            "к обновлениям без повторного скачивания и без удаления сторонних модов.\n" +
            "Если хеши не совпадут, никаких файлов изменено не будет.",
            "Подключить установленную TechQuest",
            MessageBoxButtons.YesNo, MessageBoxIcon.Question);
        if (answer != DialogResult.Yes) return;
        SetBusy(true, false);
        try
        {
            status.Text = "Проверяем существующие файлы; это может занять некоторое время…";
            await Task.Run(() =>
            {
                using var stream = GetEmbeddedPack();
                TransactionalMods.RecordInitialInstallation(root, stream);
            });
            status.Text = "TechQuest подключён к лаунчеру. Миры и настройки не затронуты.";
            RefreshProfileStatus();
            MessageBox.Show(this,
                "Установленная TechQuest подтверждена по SHA-512 и добавлена в систему обновлений.\n" +
                "Теперь можно проверять и обновлять файлы без переустановки всей сборки.",
                "Сборка подключена", MessageBoxButtons.OK, MessageBoxIcon.Information);
        }
        catch (Exception ex)
        {
            status.Text = "Подключение отклонено. Никакие моды не были изменены.";
            MessageBox.Show(this,
                "Не удалось подтвердить, что это тот же набор модов.\n" +
                "Для безопасности не удаляем и не заменяем имеющиеся файлы.\n\n" +
                ex.Message,
                "Сборка не распознана", MessageBoxButtons.OK, MessageBoxIcon.Warning);
        }
        finally
        {
            SetBusy(false, false);
            RefreshProfileStatus();
        }
    }

    private async Task VerifyExistingAsync()
    {
        string root = Path.GetFullPath(location.Text);
        SetBusy(true, false);
        try
        {
            status.Text = "Проверяем SHA-512 управляемых модов. Данные игрока не читаются…";
            int count = await Task.Run(() =>
            {
                var state = TransactionalMods.GetInstalled(root)
                    ?? throw new InvalidDataException("Не найдены данные установки TechQuest");
                foreach (var mod in state.Mods)
                    ReleaseUpdates.VerifyFile(Path.Combine(root, "mods", mod.Name), mod);
                return state.Mods.Count;
            });
            status.Text = "Проверено " + count + " модов. Повреждений не обнаружено.";
        }
        catch (Exception)
        {
            status.Text = "Некоторые управляемые моды отсутствуют или изменены.";
            MessageBox.Show(this,
                "Проверка обнаружила отсутствие или изменение управляемого файла.\n" +
                "Вы можете восстановить отсутствующие JAR по подписанному манифесту " +
                "либо проверить, не был ли мод изменён вручную.\n\n" +
                "Файлы, не принадлежащие TechQuest, не будут удаляться.",
                "Проверка целостности", MessageBoxButtons.OK, MessageBoxIcon.Warning);
        }
        finally { SetBusy(false, false); RefreshProfileStatus(); }
    }

    private async Task RepairMissingAsync()
    {
        if (currentProfile != ProfileMode.Managed) return;
        string root = Path.GetFullPath(location.Text);
        if (MessageBox.Show(this,
            "Восстанавливать будем только отсутствующие JAR исходной версии TechQuest.\n" +
            "Существующие файлы, пользовательские моды, миры и настройки не изменяются.\n" +
            "Если версия отличается от встроенной, лаунчер предложит подписанное обновление.",
            "Восстановить отсутствующие файлы?",
            MessageBoxButtons.YesNo, MessageBoxIcon.Question) != DialogResult.Yes) return;
        cancellation = new CancellationTokenSource();
        SetBusy(true, true);
        progress.Style = ProgressBarStyle.Marquee;
        try
        {
            using var embedded = GetEmbeddedPack();
            int recovered = await TransactionalMods.RestoreMissingFromEmbeddedAsync(
                root, embedded, new Progress<string>(message => status.Text = message),
                cancellation.Token);
            status.Text = recovered == 0
                ? "Все управляемые моды на месте и прошли проверку SHA-512."
                : $"Восстановлено отсутствующих модов: {recovered}.";
        }
        catch (OperationCanceledException)
        {
            status.Text = "Восстановление отменено. Установленные файлы сохранены.";
        }
        catch (Exception)
        {
            status.Text = "Восстановление остановлено: обнаружено несовпадение версии или файла.";
            MessageBox.Show(this,
                "Нельзя безопасно восстановить моды из встроенного пакета.\n" +
                "Проверьте текущую версию и подписанные обновления. " +
                "Изменённые JAR не перезаписываются автоматически.",
                "Восстановление остановлено", MessageBoxButtons.OK, MessageBoxIcon.Warning);
        }
        finally
        {
            progress.Style = ProgressBarStyle.Continuous;
            SetBusy(false, false);
            cancellation.Dispose();
            cancellation = null;
            RefreshProfileStatus();
        }
    }

    private void LaunchMinecraftOfficially()
    {
        string[] paths =
        {
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86),
                "Minecraft Launcher", "MinecraftLauncher.exe"),
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),
                "Minecraft Launcher", "MinecraftLauncher.exe")
        };
        string? executable = paths.FirstOrDefault(File.Exists);
        if (executable is null)
        {
            MessageBox.Show(this,
                "Запустите установленный официальный Minecraft Launcher через меню «Пуск».\n" +
                "В Minecraft Launcher выберите профиль NeoForge 21.1.264 и укажите папку этой сборки " +
                "в поле Game Directory:\n\n" + Path.GetFullPath(location.Text) + "\n\n" +
                "Для игры требуется купленная Minecraft Java Edition и вход в Microsoft.",
                "Официальный Minecraft Launcher",
                MessageBoxButtons.OK, MessageBoxIcon.Information);
            return;
        }
        try
        {
            Process.Start(new ProcessStartInfo(executable) { UseShellExecute = true });
            status.Text = "Открыт официальный Minecraft Launcher. Выберите профиль NeoForge 21.1.264.";
        }
        catch
        {
            MessageBox.Show(this, "Не удалось открыть Minecraft Launcher автоматически. " +
                "Запустите его через меню «Пуск». Никакие учётные данные не требуются в TechQuest.",
                "Minecraft Launcher", MessageBoxButtons.OK, MessageBoxIcon.Information);
        }
    }
}
