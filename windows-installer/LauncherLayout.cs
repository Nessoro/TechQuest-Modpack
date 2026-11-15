using System.Drawing;
using System.Windows.Forms;

namespace TechQuestInstaller;

// Presentation only. Installation, downloads and security rules remain in Program.cs
// and TransactionalMods.cs. No WebView, telemetry SDK or custom login window.
internal sealed partial class InstallerForm
{
    private static readonly Color WindowBackground = Color.FromArgb(12, 19, 30);
    private static readonly Color PanelBackground = Color.FromArgb(22, 33, 49);
    private static readonly Color SubtleBackground = Color.FromArgb(30, 44, 64);
    private static readonly Color PrimaryAccent = Color.FromArgb(173, 232, 116);
    private static readonly Color MutedText = Color.FromArgb(168, 185, 203);

    private readonly Label profileBadge = new()
    {
        AutoSize = false, Height = 34, TextAlign = ContentAlignment.MiddleLeft,
        Text = "Проверяем выбранную папку…"
    };
    private readonly Label releaseStatus = new()
    {
        AutoSize = false, Height = 48, TextAlign = ContentAlignment.MiddleLeft,
        Text = "Проверка обновлений не выполнялась"
    };
    private readonly Button playOfficial = new()
    {
        Text = "Открыть Minecraft Launcher", Height = 46, AutoSize = false
    };
    private readonly Button verifyIntegrity = new()
    {
        Text = "Проверить файлы", Height = 40, AutoSize = false
    };

    private static Label Caption(string text, float size, Color color, bool bold = false)
    {
        return new Label
        {
            Text = text, Dock = DockStyle.Fill, AutoSize = false,
            ForeColor = color, TextAlign = ContentAlignment.MiddleLeft,
            Font = new Font("Segoe UI", size, bold ? FontStyle.Bold : FontStyle.Regular)
        };
    }

    private static TableLayoutPanel Stack(params (Control control, int height)[] entries)
    {
        var p = new TableLayoutPanel
        {
            ColumnCount = 1, RowCount = entries.Length,
            Dock = DockStyle.Top, AutoSize = true, GrowStyle = TableLayoutPanelGrowStyle.FixedSize,
            Margin = new Padding(0), Padding = new Padding(0)
        };
        p.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100f));
        foreach (var (control, height) in entries)
        {
            p.RowStyles.Add(new RowStyle(SizeType.Absolute, height));
            control.Margin = new Padding(0);
            control.Dock = DockStyle.Fill;
            p.Controls.Add(control);
        }
        return p;
    }

    private static Panel Surface(Control content, int padding = 20)
    {
        var container = new Panel
        {
            BackColor = PanelBackground, Dock = DockStyle.Fill,
            Padding = new Padding(padding), Margin = new Padding(0)
        };
        container.Controls.Add(content);
        return container;
    }

    private static void StyleButton(Button button, bool primary = false)
    {
        button.FlatStyle = FlatStyle.Flat;
        button.FlatAppearance.BorderSize = 0;
        button.Font = new Font("Segoe UI", 10F, FontStyle.Bold);
        button.BackColor = primary ? PrimaryAccent : SubtleBackground;
        button.ForeColor = primary ? Color.FromArgb(18, 31, 18) : Color.WhiteSmoke;
        button.Cursor = Cursors.Hand;
        button.Margin = new Padding(0, 0, 8, 0);
        button.UseVisualStyleBackColor = false;
    }

    private static TableLayoutPanel ActionRow(params (Control control, float width)[] entries)
    {
        var p = new TableLayoutPanel
        {
            ColumnCount = entries.Length, RowCount = 1,
            Dock = DockStyle.Fill, Margin = new Padding(0)
        };
        foreach (var (control, width) in entries)
        {
            p.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, width));
            control.Dock = DockStyle.Fill;
            p.Controls.Add(control);
        }
        p.RowStyles.Add(new RowStyle(SizeType.Percent, 100f));
        return p;
    }

    private void BuildLauncherLayout()
    {
        Text = "TechQuest Launcher — Minecraft Java 1.21.1";
        ClientSize = new Size(1040, 755);
        MinimumSize = new Size(940, 735);
        StartPosition = FormStartPosition.CenterScreen;
        FormBorderStyle = FormBorderStyle.Sizable;
        MaximizeBox = true;
        BackColor = WindowBackground;
        ForeColor = Color.WhiteSmoke;
        Font = new Font("Segoe UI", 10F);
        AutoScaleMode = AutoScaleMode.Dpi;
        DoubleBuffered = true;

        foreach (Button b in new[] { install, neoforge, browse, openFolder, help, importAmw,
                                       cancel, checkUpdates, applyUpdate, rollback, downloadExe,
                                       playOfficial, verifyIntegrity })
            StyleButton(b, b == install);

        install.Text = "Установить TechQuest";
        neoforge.Text = "Установить NeoForge";
        openFolder.Text = "Папка сборки";
        checkUpdates.Text = "Проверить обновления";
        applyUpdate.Text = "Обновить моды";
        rollback.Text = "Откат версии";
        downloadExe.Text = "Обновить приложение";
        cancel.Text = "Отменить";
        importAmw.Text = "Добавить AMW вручную";
        browse.Text = "Выбрать…";
        help.Text = "Как играть";
        previewUpdates.Text = "Получать тестовые версии";
        previewUpdates.Checked = false; // No prereleases without explicit user opt-in.
        previewUpdates.ForeColor = MutedText;
        previewUpdates.AutoSize = true;

        location.BorderStyle = BorderStyle.FixedSingle;
        location.BackColor = Color.FromArgb(37, 50, 69);
        location.ForeColor = Color.WhiteSmoke;
        location.Font = new Font("Segoe UI", 10F);
        location.Dock = DockStyle.Fill;
        location.Margin = new Padding(0, 5, 10, 5);
        status.ForeColor = MutedText;
        status.TextAlign = ContentAlignment.MiddleLeft;
        status.AutoSize = false;
        status.Text = "Выберите папку игры. Личные файлы не удаляются.";
        progress.Dock = DockStyle.Fill;
        progress.Style = ProgressBarStyle.Continuous;
        progress.MarqueeAnimationSpeed = 25;
        profileBadge.ForeColor = PrimaryAccent;
        releaseStatus.ForeColor = MutedText;

        var header = Stack(
            (Caption("TECHQUEST", 25, PrimaryAccent, true), 52),
            (Caption("INDUSTRIAL FRONTIER   /   MINECRAFT JAVA 1.21.1   /   NEOFORGE 21.1.264", 9, MutedText), 26)
        );
        header.Dock = DockStyle.Fill;

        var pathRow = ActionRow((location, 78f), (browse, 22f));
        var profile = Stack(
            (Caption("ВАША СБОРКА", 14, Color.WhiteSmoke, true), 39),
            (Caption("Выберите отдельную папку TechQuest. Уже установленные моды не будут удалены.", 9, MutedText), 34),
            (pathRow, 48),
            (profileBadge, 45),
            (ActionRow((install, 50f), (playOfficial, 50f)), 53),
            (ActionRow((verifyIntegrity, 50f), (openFolder, 50f)), 48)
        );
        var downloads = Stack(
            (Caption("УСТАНОВКА И ЗАГРУЗКИ", 12, Color.WhiteSmoke, true), 38),
            (progress, 27),
            (status, 80),
            (ActionRow((cancel, 30f), (Caption("HTTPS • SHA-512 • без доступа к паролям", 9, MutedText), 70f)), 38)
        );
        var left = new TableLayoutPanel
        {
            Dock = DockStyle.Fill, ColumnCount = 1, RowCount = 3,
            Margin = new Padding(0), Padding = new Padding(0)
        };
        left.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        left.RowStyles.Add(new RowStyle(SizeType.Absolute, 92));
        left.RowStyles.Add(new RowStyle(SizeType.Absolute, 330));
        left.RowStyles.Add(new RowStyle(SizeType.Absolute, 220));
        left.Controls.Add(header, 0, 0);
        left.Controls.Add(Surface(profile), 0, 1);
        left.Controls.Add(Surface(downloads), 0, 2);

        var updates = Stack(
            (Caption("ОБНОВЛЕНИЯ", 14, Color.WhiteSmoke, true), 40),
            (releaseStatus, 75),
            (checkUpdates, 49),
            (previewUpdates, 42),
            (applyUpdate, 47),
            (rollback, 47),
            (downloadExe, 47)
        );
        var tools = Stack(
            (Caption("ИНСТРУМЕНТЫ", 12, Color.WhiteSmoke, true), 38),
            (neoforge, 47),
            (importAmw, 47),
            (help, 47),
            (Caption("Лицензионный Minecraft и вход Microsoft — только через официальный Launcher.", 9, MutedText), 84)
        );
        var right = new TableLayoutPanel
        {
            Dock = DockStyle.Fill, ColumnCount = 1, RowCount = 2,
            Padding = new Padding(0), Margin = new Padding(0)
        };
        right.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        right.RowStyles.Add(new RowStyle(SizeType.Absolute, 405));
        right.RowStyles.Add(new RowStyle(SizeType.Absolute, 305));
        right.Controls.Add(Surface(updates), 0, 0);
        right.Controls.Add(Surface(tools), 0, 1);

        var content = new TableLayoutPanel
        {
            Dock = DockStyle.Fill, ColumnCount = 2, RowCount = 1,
            BackColor = WindowBackground,
            Padding = new Padding(23, 24, 23, 15)
        };
        content.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 64));
        content.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 36));
        content.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        left.Margin = new Padding(0, 0, 14, 0);
        right.Margin = new Padding(0);
        content.Controls.Add(left, 0, 0);
        content.Controls.Add(right, 1, 0);
        Controls.Add(content);
    }
}
