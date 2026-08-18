using System;
using System.Drawing;
using System.Linq;
using System.Threading.Tasks;
using System.Windows.Forms;
using System.IO;
using System.Text.Json;
using System.Security.Cryptography;
using System.Text;
using System.Net.NetworkInformation;

namespace DesktopTokenGenerator;

public partial class MainForm : Form
{
    private ApiService _api;

    private string _configPath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
        "SecurePortal", "config.json");
    private AppConfig _config;

    // Shared controls
    private Label _settingsLink_Label = null!;

    public MainForm()
    {
        LoadConfig();
        _api = new ApiService(_config.ServerUrl);
        InitializeComponent();
        if (_config.IsRegistered)
            ShowTokenUI();
        else
            ShowRegisterUI();
    }

    private void InitializeComponent()
    {
        this.Text = "SecurePortal – Token Generator";
        this.Size = new Size(500, 700);
        this.MinimumSize = new Size(500, 700);
        this.FormBorderStyle = FormBorderStyle.FixedSingle;
        this.MaximizeBox = false;
        this.StartPosition = FormStartPosition.CenterScreen;
        this.BackColor = Color.FromArgb(13, 20, 40);
        this.Font = new Font("Segoe UI", 9.5f);
        this.Icon = SystemIcons.Shield;
    }

    private void LoadConfig()
    {
        try {
            if (File.Exists(_configPath))
                _config = JsonSerializer.Deserialize<AppConfig>(File.ReadAllText(_configPath)) ?? new AppConfig();
            else
                _config = new AppConfig();
        } catch { _config = new AppConfig(); }
    }

    private void SaveConfig()
    {
        Directory.CreateDirectory(Path.GetDirectoryName(_configPath)!);
        File.WriteAllText(_configPath, JsonSerializer.Serialize(_config));
    }

    // ─────────────────────────────────────────────────────────────────────────
    //  HEADER (shared)
    // ─────────────────────────────────────────────────────────────────────────
    private Panel BuildHeader()
    {
        var header = new Panel {
            Dock = DockStyle.Top,
            Height = 90,
            BackColor = Color.FromArgb(6, 11, 28),
        };

        var icon = new PictureBox {
            Image = SystemIcons.Shield.ToBitmap(),
            SizeMode = PictureBoxSizeMode.StretchImage,
            Size = new Size(38, 38),
            Location = new Point(22, 26),
        };

        var title = new Label {
            Text = "N e x t G e n Token Generator",
            Font = new Font("Segoe UI", 13f, FontStyle.Bold),
            ForeColor = Color.White,
            AutoSize = true,
            Location = new Point(72, 20),
        };

        var sub = new Label {
            Text = "Required for Internal Portal Access",
            Font = new Font("Segoe UI", 8.5f),
            ForeColor = Color.FromArgb(140, 155, 180),
            AutoSize = true,
            Location = new Point(74, 50),
        };

        var sep = new Panel {
            Dock = DockStyle.Bottom,
            Height = 2,
            BackColor = Color.FromArgb(30, 60, 100),
        };

        header.Controls.AddRange(new Control[] { icon, title, sub, sep });
        return header;
    }

    // ─────────────────────────────────────────────────────────────────────────
    //  REGISTER UI
    // ─────────────────────────────────────────────────────────────────────────
    private void ShowRegisterUI()
    {
        this.Controls.Clear();
        this.Controls.Add(BuildHeader());

        var scroll = new Panel {
            Dock = DockStyle.Fill,
            BackColor = Color.FromArgb(13, 20, 40),
            Padding = new Padding(28, 22, 28, 60),
            AutoScroll = true,
        };

        int x = 28;
        int w = 420;
        int y = 22;

        // Info Banner
        var infoBanner = new Panel {
            Location = new Point(x, y),
            Size = new Size(w, 72),
            BackColor = Color.FromArgb(18, 40, 80),
        };
        infoBanner.Paint += (s, e) => {
            using var pen = new Pen(Color.FromArgb(30, 90, 160), 1);
            e.Graphics.DrawRectangle(pen, 0, 0, infoBanner.Width - 1, infoBanner.Height - 1);
        };
        var infoIcon = new Label {
            Text = "🔒",
            Font = new Font("Segoe UI", 14f),
            Location = new Point(12, 18),
            AutoSize = true,
        };
        var infoText = new Label {
            Text = "First launch: register this device with your admin-provided\nUsername and Registration Code.",
            Font = new Font("Segoe UI", 9f),
            ForeColor = Color.FromArgb(180, 200, 230),
            Location = new Point(44, 14),
            Size = new Size(w - 56, 44),
        };
        infoBanner.Controls.AddRange(new Control[] { infoIcon, infoText });
        scroll.Controls.Add(infoBanner);
        y += 88;

        // Username
        scroll.Controls.Add(MakeLabel("Username", x, y));
        y += 22;
        var usernameBox = MakeTextBox(x, y, w, "Your SecurePortal username");
        scroll.Controls.Add(usernameBox);
        y += 48;

        // Registration Code
        scroll.Controls.Add(MakeLabel("Device Registration Code", x, y));
        y += 22;
        var regCodeBox = MakeTextBox(x, y, w, "REG-XXXXXXXX  (from your admin email)");
        scroll.Controls.Add(regCodeBox);
        y += 48;

        // Device info label
        var deviceInfoLbl = new Label {
            Text = $"Device: {Environment.MachineName}  ·  User: {Environment.UserName}",
            Font = new Font("Segoe UI", 8f),
            ForeColor = Color.FromArgb(80, 110, 150),
            Location = new Point(x, y),
            Size = new Size(w, 18),
            TextAlign = ContentAlignment.MiddleCenter,
        };
        scroll.Controls.Add(deviceInfoLbl);
        y += 28;

        // Register Button
        var regBtn = MakeButton("  🔗  Register Device", x, y, w, Color.FromArgb(14, 155, 233));
        y += 60;

        var statusLbl = new Label {
            Location = new Point(x, y),
            Size = new Size(w, 22),
            ForeColor = Color.FromArgb(140, 155, 180),
            Font = new Font("Segoe UI", 9f),
            Text = "",
            TextAlign = ContentAlignment.MiddleCenter,
        };
        scroll.Controls.Add(statusLbl);

        regBtn.Click += async (s, e) => {
            string username = usernameBox.Text.Trim();
            string regCode  = regCodeBox.Text.Trim();

            if (string.IsNullOrEmpty(username) || string.IsNullOrEmpty(regCode)) {
                MessageBox.Show("Please enter both Username and Registration Code.", "Missing Fields", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            regBtn.Enabled = false;
            regBtn.Text = "Registering…";
            statusLbl.Text = "Connecting to server…";
            statusLbl.ForeColor = Color.FromArgb(56, 189, 248);

            string deviceId       = Guid.NewGuid().ToString();
            string machineGuid    = Environment.MachineName;
            string deviceName     = Environment.MachineName;
            string windowsUser    = Environment.UserName;
            string macHash        = GetMacHash();

            var result = await _api.RegisterDeviceAsync(username, regCode, deviceId, machineGuid, deviceName, windowsUser, macHash);

            if (result.Success) {
                _config.IsRegistered = true;
                _config.DeviceId     = deviceId;
                _config.UserId       = username;
                SaveConfig();
                MessageBox.Show("✅ Device registered successfully!\n\nYou can now generate login tokens.", "Registration Complete", MessageBoxButtons.OK, MessageBoxIcon.Information);
                ShowTokenUI();
            } else {
                statusLbl.Text      = "Registration failed.";
                statusLbl.ForeColor = Color.FromArgb(248, 113, 113);
                MessageBox.Show(result.Error ?? "Unknown error.", "Registration Failed", MessageBoxButtons.OK, MessageBoxIcon.Error);
                regBtn.Enabled = true;
                regBtn.Text    = "  🔗  Register Device";
            }
        };

        scroll.Controls.Add(regBtn);
        AddSettingsBar(scroll, w, x);
        this.Controls.Add(scroll);
    }

    // ─────────────────────────────────────────────────────────────────────────
    //  TOKEN UI
    // ─────────────────────────────────────────────────────────────────────────
    private void ShowTokenUI()
    {
        this.Controls.Clear();
        this.Controls.Add(BuildHeader());

        var scroll = new Panel {
            Dock = DockStyle.Fill,
            BackColor = Color.FromArgb(13, 20, 40),
            Padding = new Padding(28, 18, 28, 60),
            AutoScroll = true,
        };

        int x = 28;
        int w = 420;
        int y = 18;

        // Info Banner
        var infoBanner = new Panel {
            Location = new Point(x, y),
            Size = new Size(w, 72),
            BackColor = Color.FromArgb(18, 40, 70),
        };
        infoBanner.Paint += (s, e) => {
            using var pen = new Pen(Color.FromArgb(25, 80, 140), 1);
            e.Graphics.DrawRectangle(pen, 0, 0, infoBanner.Width - 1, infoBanner.Height - 1);
        };
        var infoIcon = new Label { Text = "ℹ️", Font = new Font("Segoe UI", 13f), Location = new Point(12, 18), AutoSize = true };
        var infoText = new Label {
            Text = "Complete OTP verification on the website first, then\nenter your OTP + Session ID below to get your login token.",
            Font = new Font("Segoe UI", 9f),
            ForeColor = Color.FromArgb(180, 200, 230),
            Location = new Point(44, 12),
            Size = new Size(w - 56, 48),
        };
        infoBanner.Controls.AddRange(new Control[] { infoIcon, infoText });
        scroll.Controls.Add(infoBanner);
        y += 86;

        // STEP 1 – OTP
        scroll.Controls.Add(MakeStepLabel("STEP 1", "Enter 6-Digit OTP  (from your email)", x, y));
        y += 26;
        var otpBox = new TextBox {
            Location   = new Point(x, y),
            Width      = w,
            Height     = 42,
            BackColor  = Color.FromArgb(22, 35, 60),
            ForeColor  = Color.White,
            BorderStyle = BorderStyle.FixedSingle,
            Font        = new Font("Consolas", 20f, FontStyle.Bold),
            MaxLength   = 6,
            TextAlign   = HorizontalAlignment.Center,
            PlaceholderText = "● ● ● ● ● ●",
        };
        otpBox.KeyPress += (s, e) => { if (!char.IsDigit(e.KeyChar) && e.KeyChar != (char)Keys.Back) e.Handled = true; };
        scroll.Controls.Add(otpBox);
        y += 56;

        // STEP 2 – Session ID
        scroll.Controls.Add(MakeStepLabel("STEP 2", "Enter Session ID  (copied from website)", x, y));
        y += 26;
        var flowIdBox = new TextBox {
            Location    = new Point(x, y),
            Width       = w,
            BackColor   = Color.FromArgb(22, 35, 60),
            ForeColor   = Color.FromArgb(150, 170, 200),
            BorderStyle = BorderStyle.FixedSingle,
            Font        = new Font("Consolas", 10.5f),
            TextAlign   = HorizontalAlignment.Center,
            PlaceholderText = "Paste Session ID here…",
        };
        scroll.Controls.Add(flowIdBox);
        y += 46;

        // Device badge
        var deviceBadge = new Label {
            Text = $"🖥  Registered: {_config.UserId}  ·  {Environment.MachineName}",
            Font = new Font("Segoe UI", 7.5f),
            ForeColor = Color.FromArgb(60, 120, 80),
            Location = new Point(x, y),
            Size = new Size(w, 18),
            TextAlign = ContentAlignment.MiddleCenter,
        };
        scroll.Controls.Add(deviceBadge);
        y += 26;

        // Generate Button
        var genBtn = MakeButton("  🔐  Generate Secure Token", x, y, w, Color.FromArgb(10, 140, 220));
        y += 60;

        // Status label
        var statusLbl = new Label {
            Location = new Point(x, y),
            Size     = new Size(w, 22),
            ForeColor = Color.FromArgb(140, 155, 180),
            Font     = new Font("Segoe UI", 9f),
            Text     = "Enter OTP and Session ID, then click Generate.",
            TextAlign = ContentAlignment.MiddleCenter,
        };
        scroll.Controls.Add(statusLbl);
        y += 32;

        // Result Panel
        var resultPanel = new Panel {
            Location  = new Point(x, y),
            Size      = new Size(w, 130),
            BackColor = Color.FromArgb(5, 60, 45),
            Visible   = false,
        };
        resultPanel.Paint += (s, e) => {
            using var pen = new Pen(Color.FromArgb(20, 180, 120), 1);
            e.Graphics.DrawRectangle(pen, 0, 0, resultPanel.Width - 1, resultPanel.Height - 1);
        };

        var tokenHeader = new Label {
            Text      = "LOGIN TOKEN GENERATED",
            Font      = new Font("Segoe UI", 9f, FontStyle.Bold),
            ForeColor = Color.FromArgb(100, 220, 160),
            Location  = new Point(0, 12),
            Size      = new Size(w, 22),
            TextAlign = ContentAlignment.MiddleCenter,
        };
        var tokenBox = new TextBox {
            Location    = new Point(20, 40),
            Size        = new Size(w - 40, 40),
            BackColor   = Color.FromArgb(5, 60, 45),
            ForeColor   = Color.White,
            Font        = new Font("Consolas", 22f, FontStyle.Bold),
            BorderStyle = BorderStyle.None,
            ReadOnly    = true,
            TextAlign   = HorizontalAlignment.Center,
        };
        var copyBtn = new Button {
            Text      = "Copy Token",
            Location  = new Point((w - 180) / 2, 88),
            Size      = new Size(180, 32),
            BackColor = Color.FromArgb(16, 185, 129),
            ForeColor = Color.White,
            FlatStyle = FlatStyle.Flat,
            Font      = new Font("Segoe UI", 9f, FontStyle.Bold),
            Cursor    = Cursors.Hand,
        };
        copyBtn.FlatAppearance.BorderSize = 0;
        copyBtn.Click += (s, e) => {
            if (!string.IsNullOrEmpty(tokenBox.Text)) {
                Clipboard.SetText(tokenBox.Text);
                copyBtn.Text      = "✓ Copied!";
                copyBtn.BackColor = Color.FromArgb(5, 150, 105);
                Task.Delay(2000).ContinueWith(_ => this.Invoke(() => {
                    copyBtn.Text      = "Copy Token";
                    copyBtn.BackColor = Color.FromArgb(16, 185, 129);
                }));
            }
        };
        resultPanel.Controls.AddRange(new Control[] { tokenHeader, tokenBox, copyBtn });
        scroll.Controls.Add(resultPanel);
        y += 140;

        // Warning
        var warnLbl = new Label {
            Location  = new Point(x, y),
            Size      = new Size(w, 36),
            ForeColor = Color.FromArgb(220, 150, 30),
            Font      = new Font("Segoe UI", 8.5f),
            Text      = "⚠  Enter this token on the website within 4 minutes\nIt is single-use only.",
            TextAlign = ContentAlignment.MiddleCenter,
            Visible   = false,
        };
        scroll.Controls.Add(warnLbl);

        genBtn.Click += async (s, e) => {
            string otp    = otpBox.Text.Trim();
            string flowId = flowIdBox.Text.Trim();

            if (otp.Length != 6 || !otp.All(char.IsDigit)) {
                SetStatus(statusLbl, "Please enter a valid 6-digit OTP.", Color.FromArgb(248, 113, 113));
                return;
            }
            if (string.IsNullOrWhiteSpace(flowId)) {
                SetStatus(statusLbl, "Please paste the Session ID from the website.", Color.FromArgb(248, 113, 113));
                return;
            }

            genBtn.Enabled = false;
            genBtn.Text    = "Connecting…";
            resultPanel.Visible = false;
            warnLbl.Visible     = false;
            SetStatus(statusLbl, "Sending request to SecurePortal server…", Color.FromArgb(56, 189, 248));

            try {
                var result = await _api.GenerateTokenAsync(flowId, otp, _config.UserId, _config.DeviceId);

                if (result.Success && !string.IsNullOrEmpty(result.Token)) {
                    tokenBox.Text       = result.Token;
                    resultPanel.Visible = true;
                    warnLbl.Visible     = true;
                    otpBox.Clear();
                    SetStatus(statusLbl, "Token generated successfully!", Color.FromArgb(52, 211, 153));
                } else {
                    SetStatus(statusLbl, result.Error ?? "Unknown error.", Color.FromArgb(248, 113, 113));
                    MessageBox.Show(result.Error ?? "Unknown error.", "Error", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                }
            } catch (Exception ex) {
                SetStatus(statusLbl, $"Error: {ex.Message}", Color.FromArgb(248, 113, 113));
            } finally {
                genBtn.Enabled = true;
                genBtn.Text    = "  🔐  Generate Secure Token";
            }
        };

        scroll.Controls.Add(genBtn);
        AddSettingsBar(scroll, w, x);
        this.Controls.Add(scroll);
    }

    // ─────────────────────────────────────────────────────────────────────────
    //  Helpers
    // ─────────────────────────────────────────────────────────────────────────
    private Label MakeLabel(string text, int x, int y)
    {
        return new Label {
            Text      = text,
            Location  = new Point(x, y),
            AutoSize  = true,
            ForeColor = Color.FromArgb(140, 165, 200),
            Font      = new Font("Segoe UI", 8.5f, FontStyle.Bold),
        };
    }

    private Label MakeStepLabel(string step, string desc, int x, int y)
    {
        var lbl = new Label {
            Location = new Point(x, y),
            Size = new Size(420, 22),
            ForeColor = Color.FromArgb(140, 165, 200),
            Font = new Font("Segoe UI", 8.5f, FontStyle.Bold),
        };
        lbl.Text = $"{step}  —  {desc}";
        return lbl;
    }

    private TextBox MakeTextBox(int x, int y, int w, string placeholder)
    {
        return new TextBox {
            Location        = new Point(x, y),
            Width           = w,
            BackColor       = Color.FromArgb(22, 35, 60),
            ForeColor       = Color.White,
            BorderStyle     = BorderStyle.FixedSingle,
            Font            = new Font("Consolas", 11f),
            PlaceholderText = placeholder,
        };
    }

    private Button MakeButton(string text, int x, int y, int w, Color bg)
    {
        var btn = new Button {
            Text      = text,
            Location  = new Point(x, y),
            Size      = new Size(w, 46),
            BackColor = bg,
            ForeColor = Color.White,
            FlatStyle = FlatStyle.Flat,
            Font      = new Font("Segoe UI", 11f, FontStyle.Bold),
            Cursor    = Cursors.Hand,
        };
        btn.FlatAppearance.BorderSize  = 0;
        btn.FlatAppearance.MouseOverBackColor = ControlPaint.Dark(bg, 0.1f);
        return btn;
    }

    private void SetStatus(Label lbl, string msg, Color color)
    {
        lbl.Text      = msg;
        lbl.ForeColor = color;
    }

    private void AddSettingsBar(Panel parent, int w, int x)
    {
        var lnk = new LinkLabel {
            Text      = $"⚙  Server: {_config.ServerUrl}",
            Font      = new Font("Segoe UI", 8f),
            ForeColor = Color.FromArgb(70, 90, 120),
            AutoSize  = false,
            Size      = new Size(w, 20),
            Dock      = DockStyle.Bottom,
            TextAlign = ContentAlignment.MiddleCenter,
        };
        lnk.LinkColor       = Color.FromArgb(56, 189, 248);
        lnk.ActiveLinkColor = Color.White;
        lnk.LinkClicked    += ChangeServerUrl;
        parent.Controls.Add(lnk);
    }

    private string GetMacHash()
    {
        try {
            var mac = NetworkInterface.GetAllNetworkInterfaces()
                .FirstOrDefault(n => n.OperationalStatus == OperationalStatus.Up &&
                                     n.NetworkInterfaceType != NetworkInterfaceType.Loopback)
                ?.GetPhysicalAddress().ToString() ?? "UNKNOWN";
            using var sha = SHA256.Create();
            return BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(mac))).Replace("-", "").ToLower();
        } catch { return "ERROR_MAC"; }
    }

    private void ChangeServerUrl(object? sender, LinkLabelLinkClickedEventArgs e)
    {
        var dlg = new Form {
            Width = 420, Height = 200,
            FormBorderStyle = FormBorderStyle.FixedDialog,
            Text = "Server Settings",
            StartPosition = FormStartPosition.CenterParent,
            MaximizeBox = false, MinimizeBox = false,
            BackColor = Color.FromArgb(13, 20, 40),
            ForeColor = Color.White,
        };
        var lbl   = new Label { Left = 20, Top = 18, Width = 370, Text = "Enter SecurePortal backend URL:\n(e.g. http://127.0.0.1:8000)", ForeColor = Color.FromArgb(160, 180, 210) };
        var tb    = new TextBox { Left = 20, Top = 62, Width = 370, Text = _config.ServerUrl, BackColor = Color.FromArgb(22, 35, 60), ForeColor = Color.White, BorderStyle = BorderStyle.FixedSingle };
        var ok    = new Button { Text = "Save",   Left = 160, Top = 104, Width = 110, BackColor = Color.FromArgb(14, 155, 233), ForeColor = Color.White, FlatStyle = FlatStyle.Flat };
        var cancel= new Button { Text = "Cancel", Left = 278, Top = 104, Width = 110, BackColor = Color.FromArgb(40, 55, 80),   ForeColor = Color.White, FlatStyle = FlatStyle.Flat };
        ok.FlatAppearance.BorderSize = cancel.FlatAppearance.BorderSize = 0;
        ok.Click     += (_, _) => { dlg.DialogResult = DialogResult.OK;     dlg.Close(); };
        cancel.Click += (_, _) => { dlg.DialogResult = DialogResult.Cancel; dlg.Close(); };
        dlg.Controls.AddRange(new Control[] { lbl, tb, ok, cancel });
        dlg.AcceptButton = ok; dlg.CancelButton = cancel;

        if (dlg.ShowDialog(this) == DialogResult.OK && !string.IsNullOrWhiteSpace(tb.Text)) {
            _config.ServerUrl = tb.Text.TrimEnd('/');
            SaveConfig();
            _api = new ApiService(_config.ServerUrl);
            if (_config.IsRegistered) ShowTokenUI(); else ShowRegisterUI();
        }
    }
}

public class AppConfig
{
    public string ServerUrl  { get; set; } = "http://127.0.0.1:8000";
    public bool   IsRegistered { get; set; } = false;
    public string DeviceId   { get; set; } = "";
    public string UserId     { get; set; } = "";
}
