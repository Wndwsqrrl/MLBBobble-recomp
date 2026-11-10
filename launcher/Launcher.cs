using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.Windows.Forms;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;
using System.Collections.Generic;

static class Theme {
    public static Color Blue   = Color.FromArgb(46, 74, 214);
    public static Color Purple = Color.FromArgb(132, 56, 184);
    public static Color Ink    = Color.FromArgb(236, 238, 242);
    public static Color Muted  = Color.FromArgb(190, 194, 206);
    public static Color Good   = Color.FromArgb(120, 220, 150);
    public static Color Bad    = Color.FromArgb(240, 120, 120);

    public static GraphicsPath Rounded(Rectangle r, int radius) {
        int d = Math.Max(2, radius * 2);
        var p = new GraphicsPath();
        p.AddArc(r.X, r.Y, d, d, 180, 90);
        p.AddArc(r.Right - d, r.Y, d, d, 270, 90);
        p.AddArc(r.Right - d, r.Bottom - d, d, d, 0, 90);
        p.AddArc(r.X, r.Bottom - d, d, d, 90, 90);
        p.CloseFigure();
        return p;
    }
    public static void FillGradient(Graphics g, Rectangle r, Color a, Color b, float angle) {
        if (r.Width <= 0 || r.Height <= 0) return;
        using (var br = new LinearGradientBrush(r, a, b, angle)) g.FillRectangle(br, r);
    }
}

class GameDef {
    public string Key, Name, Exe, Data;
    public string[] Icons;
    public bool Installed {
        get {
            try { return File.Exists(Exe) && File.Exists(Path.Combine(Data, "default.xex")); }
            catch { return false; }
        }
    }
    public Image LoadArt() {
        foreach (var p in Icons) { try { if (File.Exists(p)) return Image.FromFile(p); } catch { } }
        return null;
    }
}

static class Config {
    static string Path_ { get { return Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "launcher.cfg"); } }
    public static Dictionary<string, string> Load() {
        var d = new Dictionary<string, string>();
        try {
            if (File.Exists(Path_))
                foreach (var ln in File.ReadAllLines(Path_)) {
                    int i = ln.IndexOf('=');
                    if (i > 0) d[ln.Substring(0, i).Trim()] = ln.Substring(i + 1).Trim();
                }
        } catch { }
        return d;
    }
    public static void Save(IEnumerable<GameDef> games) {
        try {
            var sb = new StringBuilder();
            foreach (var g in games) { sb.AppendLine(g.Key + "_exe=" + g.Exe); sb.AppendLine(g.Key + "_data=" + g.Data); }
            File.WriteAllText(Path_, sb.ToString());
        } catch { }
    }
}

// Roster update for MLB Bobblehead Pros: the Oct 2011 title-content package (an
// Xbox 360 STFS file, "MLB Bobblehead Pros - Roster Update Oct.11") carries two
// replacement roster files. The game never mounts the package itself, so the
// launcher copies them over the base rosters in the game folder, keeping the
// originals in <game>\_roster_backup\ so the change can be undone.
static class RosterUpdate {
    const uint TitleId = 0x58410B7B;
    const int Block = 0x1000;
    // package path -> path in the game folder (relative to the folder with default.xex)
    static readonly string[,] Files = {
        { "data/xbox360_us/player/data/PLAYER_DATA_OCT2011.CHK",
          @"data\xbox360_us\player\data\PLAYER_DATA.CHK" },
        { "data/xbox360_us/player/season_data/SEASON_PLAYER_DATA_OCT2011.CHK",
          @"data\xbox360_us\player\season_data\SEASON_PLAYER_DATA.CHK" },
    };

    static string BackupDir(string data) { return Path.Combine(data, "_roster_backup"); }

    public static bool IsApplied(string data) {
        try {
            for (int i = 0; i < Files.GetLength(0); i++) {
                string target = Path.Combine(data, Files[i, 1]);
                string backup = Path.Combine(BackupDir(data), Path.GetFileName(Files[i, 1]));
                if (!File.Exists(target) || !File.Exists(backup)) return false;
                if (SameBytes(target, backup)) return false;
            }
            return true;
        } catch { return false; }
    }

    static bool SameBytes(string a, string b) {
        var x = File.ReadAllBytes(a); var y = File.ReadAllBytes(b);
        if (x.Length != y.Length) return false;
        for (int i = 0; i < x.Length; i++) if (x[i] != y[i]) return false;
        return true;
    }

    // Returns null on success, otherwise a message for the user.
    public static string Apply(string package, string data) {
        byte[] pkg;
        try { pkg = File.ReadAllBytes(package); } catch (Exception ex) { return "Could not read the file:\n" + ex.Message; }
        if (pkg.Length < 0x3000) return "That file is too small to be an Xbox 360 content package.";
        string magic = Encoding.ASCII.GetString(pkg, 0, 4);
        if (magic != "CON " && magic != "LIVE" && magic != "PIRS")
            return "That is not an Xbox 360 content package (STFS).\n\n"
                 + "If you have the .7z download, extract it first and choose the file inside\n"
                 + "58410B7B\\00000002\\.";
        if (BE32(pkg, 0x360) != TitleId) return "That package is for a different game (not MLB Bobblehead Pros).";

        var found = new byte[Files.GetLength(0)][];
        var entries = ReadFileTable(pkg);
        if (entries == null) return "Could not read the package's file table.";
        for (int i = 0; i < Files.GetLength(0); i++) {
            Entry e;
            if (!entries.TryGetValue(Files[i, 0].ToUpperInvariant(), out e))
                return "This package does not contain the Oct 2011 roster update\n(missing " + Files[i, 0] + ").";
            byte[] bytes = ReadFile(pkg, e);
            if (bytes == null || bytes.Length < 4 || Encoding.ASCII.GetString(bytes, 0, 4) != "CHK ")
                return "The roster data in this package could not be read correctly.";
            found[i] = bytes;
        }

        try {
            Directory.CreateDirectory(BackupDir(data));
            for (int i = 0; i < Files.GetLength(0); i++) {
                string target = Path.Combine(data, Files[i, 1]);
                if (!File.Exists(target)) return "The game folder is missing " + Files[i, 1] + ".";
                // Keep the first backup forever: it holds the disc's original rosters.
                string backup = Path.Combine(BackupDir(data), Path.GetFileName(Files[i, 1]));
                if (!File.Exists(backup)) File.Copy(target, backup);
            }
            for (int i = 0; i < Files.GetLength(0); i++)
                File.WriteAllBytes(Path.Combine(data, Files[i, 1]), found[i]);
        } catch (Exception ex) { return "Could not write the roster files:\n" + ex.Message; }
        return null;
    }

    public static string Restore(string data) {
        try {
            for (int i = 0; i < Files.GetLength(0); i++) {
                string backup = Path.Combine(BackupDir(data), Path.GetFileName(Files[i, 1]));
                if (!File.Exists(backup)) return "No backup of the original rosters was found.";
            }
            for (int i = 0; i < Files.GetLength(0); i++)
                File.Copy(Path.Combine(BackupDir(data), Path.GetFileName(Files[i, 1])),
                          Path.Combine(data, Files[i, 1]), true);
        } catch (Exception ex) { return "Could not restore the roster files:\n" + ex.Message; }
        return null;
    }

    // --- minimal STFS reader (read-only, contiguous files) -------------------------------------

    class Entry { public int Start; public int Size; public bool Contiguous; }

    static uint BE32(byte[] b, int o) { return (uint)(b[o] << 24 | b[o + 1] << 16 | b[o + 2] << 8 | b[o + 3]); }
    static int LE24(byte[] b, int o) { return b[o] | b[o + 1] << 8 | b[o + 2] << 16; }

    // Data block number -> physical block, skipping the interleaved level-0/1/2 hash tables.
    static long Backing(long b, int shift) {
        long t = (((b + 0xAA) / 0xAA) << shift) + b;
        if (b < 0xAA) return t;
        t += ((b + 0x70E4) / 0x70E4) << shift;
        if (b < 0x70E4) return t;
        return t + (((b + 0x4AF768) / 0x4AF768) << shift);
    }

    static long Offset(byte[] pkg, long block, int shift) {
        long headerSize = BE32(pkg, 0x340);
        long baseOff = (headerSize + 0xFFF) & ~0xFFFL;
        return baseOff + Backing(block, shift) * Block;
    }

    static int Shift;

    static Dictionary<string, Entry> ReadFileTable(byte[] pkg) {
        int count = pkg[0x37C] | pkg[0x37D] << 8;
        int first = LE24(pkg, 0x37E);
        int sep = pkg[0x37B] & 1;
        // The table-size bit is not always set as documented: accept whichever reading gives
        // printable names.
        foreach (int shift in new[] { sep, 1 - sep }) {
            var names = new List<string>(); var parents = new List<int>(); var raw = new List<Entry>();
            var dirs = new List<bool>();
            bool ok = true;
            for (int bi = 0; bi < Math.Max(count, 1) && ok; bi++) {
                long off = Offset(pkg, first + bi, shift);
                if (off < 0 || off + Block > pkg.Length) { ok = false; break; }
                for (int j = 0; j < Block; j += 0x40) {
                    long e = off + j;
                    int flags = pkg[e + 0x28], len = flags & 0x3F;
                    if (len == 0) continue;
                    for (int k = 0; k < len; k++) { byte c = pkg[e + k]; if (c < 32 || c >= 127) ok = false; }
                    if (!ok) break;
                    names.Add(Encoding.ASCII.GetString(pkg, (int)e, len));
                    dirs.Add((flags & 0x80) != 0);
                    parents.Add(pkg[e + 0x32] << 8 | pkg[e + 0x33]);
                    raw.Add(new Entry { Start = LE24(pkg, (int)e + 0x2F), Size = (int)BE32(pkg, (int)e + 0x34),
                                        Contiguous = (flags & 0x40) != 0 });
                }
            }
            if (!ok || names.Count == 0) continue;
            Shift = shift;
            var result = new Dictionary<string, Entry>();
            for (int i = 0; i < names.Count; i++) {
                if (dirs[i]) continue;
                string path = names[i]; int p = parents[i], guard = 0;
                while (p != 0xFFFF && p >= 0 && p < names.Count && guard++ < 64) { path = names[p] + "/" + path; p = parents[p]; }
                result[path.ToUpperInvariant()] = raw[i];
            }
            return result;
        }
        return null;
    }

    static byte[] ReadFile(byte[] pkg, Entry e) {
        if (!e.Contiguous && e.Size > Block) return null;   // would need the hash-chain walk
        var outp = new byte[e.Size];
        int done = 0;
        for (long k = 0; done < e.Size; k++) {
            long off = Offset(pkg, e.Start + k, Shift);
            int n = Math.Min(Block, e.Size - done);
            if (off + n > pkg.Length) return null;
            Buffer.BlockCopy(pkg, (int)off, outp, done, n);
            done += n;
        }
        return outp;
    }
}

class RoundButton : Button {
    public RoundButton() {
        FlatStyle = FlatStyle.Flat; FlatAppearance.BorderSize = 0;
        BackColor = Color.Transparent; ForeColor = Theme.Ink;
        Font = new Font("Segoe UI", 10, FontStyle.Bold); Cursor = Cursors.Hand;
        SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer
               | ControlStyles.UserPaint | ControlStyles.SupportsTransparentBackColor, true);
        MouseEnter += delegate { Invalidate(); }; MouseLeave += delegate { Invalidate(); };
    }
    protected override void OnResize(EventArgs e) {
        base.OnResize(e);
        using (var p = Theme.Rounded(new Rectangle(0, 0, Width, Height), Height / 2)) Region = new Region(p);
    }
    protected override void OnPaint(PaintEventArgs e) {
        var g = e.Graphics; g.SmoothingMode = SmoothingMode.AntiAlias;
        var r = new Rectangle(0, 0, Width, Height);
        bool hot = ClientRectangle.Contains(PointToClient(Cursor.Position));
        using (var path = Theme.Rounded(new Rectangle(0, 0, Width - 1, Height - 1), Height / 2)) {
            var a = hot ? ControlPaint.Light(Theme.Blue, 0.15f) : Theme.Blue;
            var b = hot ? ControlPaint.Light(Theme.Purple, 0.15f) : Theme.Purple;
            using (var br = new LinearGradientBrush(r, a, b, 0f)) g.FillPath(br, path);
        }
        TextRenderer.DrawText(g, Text, Font, r, ForeColor,
            TextFormatFlags.HorizontalCenter | TextFormatFlags.VerticalCenter);
    }
}

class Card : Panel {
    GameDef g; Image img; bool hover;
    public Action OnSetup;
    public Card(GameDef game) {
        g = game; img = g.LoadArt();
        DoubleBuffered = true; Cursor = Cursors.Hand;
        MouseEnter += delegate { hover = true; Invalidate(); };
        MouseLeave += delegate { hover = false; Invalidate(); };
        Click += delegate { Activate(); };
    }
    void Activate() {
        if (!g.Installed) { if (OnSetup != null) OnSetup(); return; }
        try {
            var psi = new ProcessStartInfo(g.Exe, "--game_data_root=\"" + g.Data + "\"");
            psi.WorkingDirectory = Path.GetDirectoryName(g.Exe);
            psi.UseShellExecute = true;
            Process.Start(psi);
        } catch (Exception ex) {
            MessageBox.Show("Failed to launch:\n" + ex.Message, "Launcher",
                MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }
    protected override void OnResize(EventArgs e) {
        base.OnResize(e);
        using (var p = Theme.Rounded(new Rectangle(0, 0, Width, Height), 24)) Region = new Region(p);
    }
    static Rectangle Cover(Size src, Size box) {
        float ar = (float)src.Width / src.Height, br = (float)box.Width / box.Height;
        int w, h;
        if (ar > br) { h = box.Height; w = (int)(h * ar); } else { w = box.Width; h = (int)(w / ar); }
        return new Rectangle((box.Width - w) / 2, (box.Height - h) / 2, w, h);
    }
    protected override void OnPaint(PaintEventArgs e) {
        var gfx = e.Graphics;
        gfx.SmoothingMode = SmoothingMode.AntiAlias;
        gfx.InterpolationMode = InterpolationMode.HighQualityBicubic;
        gfx.PixelOffsetMode = PixelOffsetMode.HighQuality;
        bool ok = g.Installed;

        Color g1 = ok ? ControlPaint.Dark(Theme.Blue, 0.4f) : Color.FromArgb(42, 44, 50);
        Color g2 = ok ? ControlPaint.Dark(Theme.Purple, 0.4f) : Color.FromArgb(28, 29, 34);
        Theme.FillGradient(gfx, new Rectangle(0, 0, Width, Height), g1, g2, 115f);

        if (img != null) {
            ColorMatrix cm;
            if (ok) { cm = new ColorMatrix(); cm.Matrix33 = hover ? 0.95f : 0.75f; }
            else cm = new ColorMatrix(new float[][] {       // greyscale + dim when not installed
                new float[]{0.30f,0.30f,0.30f,0,0},
                new float[]{0.59f,0.59f,0.59f,0,0},
                new float[]{0.11f,0.11f,0.11f,0,0},
                new float[]{0,0,0,0.30f,0},
                new float[]{0,0,0,0,1} });
            var ia = new ImageAttributes(); ia.SetColorMatrix(cm);
            var dst = Cover(img.Size, new Size(Width, Height));
            var clip = gfx.Clip;
            using (var rp = Theme.Rounded(new Rectangle(0, 0, Width, Height), 24)) gfx.SetClip(rp, CombineMode.Intersect);
            gfx.DrawImage(img, dst, 0, 0, img.Width, img.Height, GraphicsUnit.Pixel, ia);
            gfx.Clip = clip;
        }
        using (var lg = new LinearGradientBrush(new Rectangle(0, Height - 104, Width, 104),
                   Color.FromArgb(0, 0, 0, 0), Color.FromArgb(215, 8, 6, 22), 90f))
            gfx.FillRectangle(lg, new Rectangle(0, Height - 104, Width, 104));

        using (var gp = Theme.Rounded(new Rectangle(1, 1, Width - 3, Height - 3), 23)) {
            Color a, b;
            if (ok) { a = hover ? ControlPaint.Light(Theme.Blue, 0.35f) : Theme.Blue;
                      b = hover ? ControlPaint.Light(Theme.Purple, 0.35f) : Theme.Purple; }
            else { a = Color.FromArgb(96, 100, 110); b = Color.FromArgb(72, 76, 86); }
            using (var br = new LinearGradientBrush(new Rectangle(0, 0, Width, Height), a, b, 45f))
            using (var pen = new Pen(br, hover ? 3f : 2f)) gfx.DrawPath(pen, gp);
        }
        using (var f = new Font("Segoe UI", 15, FontStyle.Bold))
        using (var white = new SolidBrush(Color.White))
        using (var sh = new SolidBrush(Color.FromArgb(205, 0, 0, 0))) {
            var sf = new StringFormat(); sf.Alignment = StringAlignment.Center; sf.LineAlignment = StringAlignment.Far;
            var tr = new RectangleF(10, Height - 62, Width - 20, 52);
            gfx.DrawString(g.Name, f, sh, new RectangleF(tr.X + 1, tr.Y + 1, tr.Width, tr.Height), sf);
            gfx.DrawString(g.Name, f, white, tr, sf);
        }
        if (!ok) {
            using (var f = new Font("Segoe UI", 11, FontStyle.Bold))
            using (var b = new SolidBrush(Theme.Bad)) {
                var sf = new StringFormat(); sf.Alignment = StringAlignment.Center;
                gfx.DrawString("Not installed - click to set up", f, b,
                    new RectangleF(10, Height / 2 - 12, Width - 20, 24), sf);
            }
        }
    }
}

class GradientForm : Form {
    public GradientForm() {
        DoubleBuffered = true; FormBorderStyle = FormBorderStyle.FixedSingle;
        MaximizeBox = false; StartPosition = FormStartPosition.CenterScreen;
        BackColor = Color.FromArgb(28, 24, 48);
    }
    protected override void OnPaintBackground(PaintEventArgs e) {
        Theme.FillGradient(e.Graphics, ClientRectangle,
            ControlPaint.Dark(Theme.Blue, 0.5f), ControlPaint.Dark(Theme.Purple, 0.5f), 120f);
    }
}

class SetupForm : GradientForm {
    List<GameDef> games;
    public SetupForm(List<GameDef> g) {
        games = g;
        Text = "Setup"; ClientSize = new Size(560, 380);
        var head = new Label { Text = "Game setup", ForeColor = Theme.Ink, Font = new Font("Segoe UI", 15),
            AutoSize = true, Location = new Point(24, 18), BackColor = Color.Transparent };
        Controls.Add(head);
        var sub = new Label { Text = "Point the launcher at each game's folder (the one containing default.xex).",
            ForeColor = Theme.Muted, Font = new Font("Segoe UI", 9), AutoSize = true,
            Location = new Point(26, 52), BackColor = Color.Transparent };
        Controls.Add(sub);

        int y = 86;
        foreach (var gd in games) BuildRow(gd, ref y);
        var pros = games.Find(gg => gg.Key == "pros");
        if (pros != null) BuildRosterRow(pros, y + 10);

        var done = new RoundButton { Text = "Done", Size = new Size(120, 42), Location = new Point(560 - 24 - 120, 380 - 58) };
        done.Click += delegate { Config.Save(games); Close(); };
        Controls.Add(done);
    }
    void BuildRow(GameDef gd, ref int y) {
        var name = new Label { Text = gd.Name, ForeColor = Theme.Ink, Font = new Font("Segoe UI", 11, FontStyle.Bold),
            AutoSize = true, Location = new Point(26, y), BackColor = Color.Transparent };
        Controls.Add(name);
        var status = new Label { ForeColor = gd.Installed ? Theme.Good : Theme.Bad, Font = new Font("Segoe UI", 10),
            AutoSize = true, Location = new Point(300, y + 1), BackColor = Color.Transparent };
        status.Text = gd.Installed ? "Installed" : "Not found";
        Controls.Add(status);
        var locate = new RoundButton { Text = "Locate folder...", Size = new Size(150, 36), Location = new Point(390, y - 4) };
        locate.Click += delegate {
            using (var fb = new FolderBrowserDialog()) {
                fb.Description = "Select the " + gd.Name + " folder (contains default.xex)";
                if (fb.ShowDialog() == DialogResult.OK) {
                    string path = fb.SelectedPath;
                    if (File.Exists(Path.Combine(path, "default.xex"))) {
                        gd.Data = path;
                        status.ForeColor = gd.Installed ? Theme.Good : Theme.Bad;
                        status.Text = gd.Installed ? "Installed" : "Exe missing";
                    } else {
                        MessageBox.Show("That folder has no default.xex.\nPick the folder that contains the game's default.xex.",
                            "Setup", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    }
                }
            }
        };
        Controls.Add(locate);
        y += 58;
    }
    void BuildRosterRow(GameDef pros, int y) {
        var name = new Label { Text = "Pros roster update (Oct 2011)", ForeColor = Theme.Ink,
            Font = new Font("Segoe UI", 11, FontStyle.Bold), AutoSize = true, Location = new Point(26, y),
            BackColor = Color.Transparent };
        Controls.Add(name);
        var status = new Label { Font = new Font("Segoe UI", 9), AutoSize = true, Location = new Point(28, y + 26),
            BackColor = Color.Transparent };
        Controls.Add(status);
        Action refresh = delegate {
            bool have = pros.Installed;
            bool on = have && RosterUpdate.IsApplied(pros.Data);
            status.ForeColor = on ? Theme.Good : Theme.Muted;
            status.Text = !have ? "Locate the Pros folder first."
                        : on ? "Applied - the game uses the updated rosters."
                             : "Not applied - choose the roster update package to install it.";
        };
        refresh();

        var apply = new RoundButton { Text = "Apply update...", Size = new Size(150, 36), Location = new Point(390, y - 4) };
        apply.Click += delegate {
            if (!pros.Installed) { MessageBox.Show("Locate the MLB Bobblehead Pros folder first.", "Roster update"); return; }
            using (var ofd = new OpenFileDialog()) {
                ofd.Title = "Choose the roster update package (inside 58410B7B\\00000002\\ of the extracted download)";
                ofd.Filter = "Xbox 360 content package (*.*)|*.*";
                if (ofd.ShowDialog() != DialogResult.OK) return;
                string err = RosterUpdate.Apply(ofd.FileName, pros.Data);
                if (err == null)
                    MessageBox.Show("Roster update installed.\nThe original rosters were saved to _roster_backup in the game folder.",
                        "Roster update", MessageBoxButtons.OK, MessageBoxIcon.Information);
                else
                    MessageBox.Show(err, "Roster update", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
            refresh();
        };
        Controls.Add(apply);

        var restore = new RoundButton { Text = "Restore", Size = new Size(100, 32), Location = new Point(440, y + 38) };
        restore.Click += delegate {
            if (!pros.Installed) return;
            string err = RosterUpdate.Restore(pros.Data);
            if (err != null) MessageBox.Show(err, "Roster update", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            refresh();
        };
        Controls.Add(restore);
    }
}

class OptionsForm : GradientForm {
    // Each game's runtime settings live next to its exe as bobblehead<game>.toml.
    readonly string[] Tomls;
    CheckBox cbFull, cbVsync, cbMnk; ComboBox cbRes;
    // Host-side resolution presets (the `resolution` cvar: output window + guest
    // video mode). Higher-than-native downsamples for a sharper image.
    static readonly string[] ResVals = { "720p", "1080p", "1440p", "4k" };
    CheckBox Make(string text, int y) {
        var c = new CheckBox { Text = text, ForeColor = Theme.Ink, Font = new Font("Segoe UI", 11),
            AutoSize = true, Location = new Point(28, y), BackColor = Color.Transparent };
        Controls.Add(c); return c;
    }
    public OptionsForm(List<GameDef> games) {
        var tomls = new List<string>();
        foreach (var g in games) {
            if (string.IsNullOrEmpty(g.Exe)) continue;
            try { tomls.Add(Path.ChangeExtension(g.Exe, ".toml")); } catch { }
        }
        Tomls = tomls.ToArray();
        Text = "Options"; ClientSize = new Size(440, 332);
        var head = new Label { Text = "Options", ForeColor = Theme.Ink, Font = new Font("Segoe UI", 15),
            AutoSize = true, Location = new Point(26, 18), BackColor = Color.Transparent };
        Controls.Add(head);

        cbVsync = Make("V-Sync", 62);
        cbMnk   = Make("Keyboard controls (play without a gamepad)", 98);
        cbFull  = Make("Fullscreen", 134);

        var lblS = new Label { Text = "Resolution", ForeColor = Theme.Ink, Font = new Font("Segoe UI", 11),
            AutoSize = true, Location = new Point(28, 176), BackColor = Color.Transparent };
        Controls.Add(lblS);
        cbRes = new ComboBox { DropDownStyle = ComboBoxStyle.DropDownList, Location = new Point(230, 172),
            Width = 180, Font = new Font("Segoe UI", 11) };
        cbRes.Items.AddRange(new object[] { "720p", "1080p", "1440p (downsampled)", "4K (downsampled)" });
        Controls.Add(cbRes);

        LoadCurrent();
        var save = new RoundButton { Text = "Save", Size = new Size(120, 42), Location = new Point(230, 254) };
        save.Click += delegate { Apply(); Close(); }; Controls.Add(save);
        var cancel = new RoundButton { Text = "Cancel", Size = new Size(120, 42), Location = new Point(90, 254) };
        cancel.Click += delegate { Close(); }; Controls.Add(cancel);
    }
    static bool ReadBool(string t, string key, bool def) {
        var m = Regex.Match(t, @"(?m)^\s*" + Regex.Escape(key) + @"\s*=\s*(true|false)");
        return m.Success ? m.Groups[1].Value == "true" : def;
    }
    void LoadCurrent() {
        cbRes.SelectedIndex = 1; cbFull.Checked = true; cbVsync.Checked = true; cbMnk.Checked = true;
        try {
            if (Tomls.Length > 0 && File.Exists(Tomls[0])) {
                string t = File.ReadAllText(Tomls[0]);
                var m = Regex.Match(t, "(?m)^\\s*resolution\\s*=\\s*\"?([0-9a-zA-Z]+)\"?");
                if (m.Success) { int i = Array.IndexOf(ResVals, m.Groups[1].Value.ToLower()); if (i >= 0) cbRes.SelectedIndex = i; }
                cbFull.Checked  = ReadBool(t, "fullscreen", true);
                cbVsync.Checked = ReadBool(t, "vsync", true);
                cbMnk.Checked   = ReadBool(t, "mnk_mode", true);
            }
        } catch { }
    }
    void Apply() {
        string res = ResVals[cbRes.SelectedIndex];
        foreach (var p in Tomls) {
            try {
                if (!File.Exists(p)) continue;
                string t = File.ReadAllText(p);
                t = SetKey(t, "resolution", "\"" + res + "\"");
                t = SetKey(t, "fullscreen", cbFull.Checked ? "true" : "false");
                t = SetKey(t, "vsync", cbVsync.Checked ? "true" : "false");
                t = SetKey(t, "mnk_mode", cbMnk.Checked ? "true" : "false");
                File.WriteAllText(p, t);
            } catch (Exception ex) { MessageBox.Show("Could not write " + p + "\n" + ex.Message, "Options"); }
        }
    }
    static string SetKey(string text, string key, string val) {
        var rx = new Regex(@"(?m)^\s*" + Regex.Escape(key) + @"\s*=.*$");
        if (rx.IsMatch(text)) return rx.Replace(text, key + " = " + val, 1);
        return text.TrimEnd() + "\r\n" + key + " = " + val + "\r\n";
    }
}

static class Program {
    static Icon LoadAppIcon(List<GameDef> games) {
        foreach (var g in games)
            foreach (var p in g.Icons) {
                try { if (File.Exists(p)) using (var bmp = new Bitmap(p)) return Icon.FromHandle(((Bitmap)bmp.Clone()).GetHicon()); }
                catch { }
            }
        return null;
    }

    [STAThread]
    static void Main(string[] args) {
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);

        string artDir = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "art");
        try { Directory.CreateDirectory(artDir); } catch { }
        var cfg = Config.Load();

        // Defaults are portable: the exe is looked for in a sibling pros/ or battle/
        // folder next to the launcher, and the game data path is left blank so the
        // first-run setup prompts for it. A saved launcher.cfg overrides both.
        string baseDir = AppDomain.CurrentDomain.BaseDirectory;
        string prosExe    = cfg.ContainsKey("pros_exe")    ? cfg["pros_exe"]    : Path.Combine(baseDir, "pros", "bobbleheadpros.exe");
        string prosData   = cfg.ContainsKey("pros_data")   ? cfg["pros_data"]   : "";
        string battleExe  = cfg.ContainsKey("battle_exe")  ? cfg["battle_exe"]  : Path.Combine(baseDir, "battle", "bobbleheadbattle.exe");
        string battleData = cfg.ContainsKey("battle_data") ? cfg["battle_data"] : "";

        var games = new List<GameDef> {
            new GameDef { Key = "pros", Name = "MLB Bobblehead Pros",
                Exe = prosExe, Data = prosData,
                Icons = new[] { Path.Combine(artDir, "pros.png"),
                                string.IsNullOrEmpty(prosData) ? "" : Path.Combine(prosData, "TitleIcon.png") } },
            new GameDef { Key = "battle", Name = "MLB Bobblehead Battle",
                Exe = battleExe, Data = battleData,
                Icons = new[] { Path.Combine(artDir, "battle.png"),
                                string.IsNullOrEmpty(battleData) ? "" : Path.Combine(battleData, "TitleIcon.png") } }
        };

        // Direct-launch support: `--play pros` / `--play battle` runs that game
        // straight away (used by the installed Start Menu game shortcuts) when it's
        // set up; otherwise it falls through to the launcher so the user can locate it.
        string playKey = null;
        for (int i = 0; i < args.Length; i++) {
            if (args[i] == "--play" && i + 1 < args.Length) playKey = args[i + 1].ToLowerInvariant();
            else if (args[i].StartsWith("--play=")) playKey = args[i].Substring(7).ToLowerInvariant();
        }
        if (playKey != null) {
            var pg = games.Find(gg => gg.Key == playKey);
            if (pg != null && pg.Installed) {
                try {
                    var psi = new ProcessStartInfo(pg.Exe, "--game_data_root=\"" + pg.Data + "\"");
                    psi.WorkingDirectory = Path.GetDirectoryName(pg.Exe); psi.UseShellExecute = true;
                    Process.Start(psi);
                    return;
                } catch { /* fall through to the launcher window */ }
            }
        }

        // startup installed-check: walk through setup if anything is missing
        bool allOk = true; foreach (var g in games) if (!g.Installed) allOk = false;
        if (!allOk) { using (var s = new SetupForm(games)) s.ShowDialog(); Config.Save(games); }

        int cw = 300, ch = 410, gap = 36, margin = 40, top = 92;
        int w = margin * 2 + cw * 2 + gap;
        int h = top + ch + 82;

        var f = new GradientForm();
        f.Text = "MLB Bobblehead - Launcher";
        f.ClientSize = new Size(w, h);
        var ic = LoadAppIcon(games); if (ic != null) f.Icon = ic;

        f.Paint += delegate (object s, PaintEventArgs e) {
            var g = e.Graphics; g.SmoothingMode = SmoothingMode.AntiAlias;
            using (var tf = new Font("Segoe UI", 20, FontStyle.Bold))
            using (var sh = new SolidBrush(Color.FromArgb(150, 0, 0, 0)))
            using (var br = new SolidBrush(Theme.Ink)) {
                g.DrawString("MLB Bobblehead", tf, sh, new PointF(margin + 1, 27));
                g.DrawString("MLB Bobblehead", tf, br, new PointF(margin, 26));
            }
            using (var hf = new Font("Segoe UI", 8.5f))
            using (var hb = new SolidBrush(Theme.Muted))
                g.DrawString("Start = Enter    A = Space    move = WASD", hf, hb, new PointF(margin, h - 40));
        };

        Card[] cards = new Card[games.Count];
        int x = margin;
        for (int i = 0; i < games.Count; i++) {
            var gd = games[i];
            var c = new Card(gd) { Size = new Size(cw, ch), Location = new Point(x, top) };
            c.OnSetup = delegate {
                using (var s = new SetupForm(games)) s.ShowDialog(f);
                Config.Save(games);
                foreach (var cc in cards) if (cc != null) cc.Invalidate();
            };
            f.Controls.Add(c); cards[i] = c; x += cw + gap;
        }

        var opt = new RoundButton { Text = "Options", Size = new Size(140, 44),
            Location = new Point(w - margin - 140, h - 56) };
        opt.Click += delegate { using (var o = new OptionsForm(games)) o.ShowDialog(f); };
        f.Controls.Add(opt);

        var setup = new RoundButton { Text = "Setup", Size = new Size(120, 44),
            Location = new Point(w - margin - 140 - 132, h - 56) };
        setup.Click += delegate {
            using (var s = new SetupForm(games)) s.ShowDialog(f);
            Config.Save(games);
            foreach (var cc in cards) if (cc != null) cc.Invalidate();
        };
        f.Controls.Add(setup);

        Application.Run(f);
    }
}
