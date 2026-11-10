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
    // SHA-256 of the default.xex these builds were recompiled from. The exe only works with
    // that exact version, so the setup screen checks the player's copy against it.
    public string XexSha;

    public static string Sha256(string path) {
        using (var h = System.Security.Cryptography.SHA256.Create())
        using (var f = File.OpenRead(path))
            return BitConverter.ToString(h.ComputeHash(f)).Replace("-", "");
    }
    public bool XexMatches(string folder) {
        try { return string.Equals(Sha256(Path.Combine(folder, "default.xex")), XexSha, StringComparison.OrdinalIgnoreCase); }
        catch { return false; }
    }
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

// Season rosters for MLB Bobblehead Pros. A roster is two files the game reads from
// its folder: player\data\PLAYER_DATA.CHK (player records + the 30 team rosters and
// both All-Star squads) and player\season_data\SEASON_PLAYER_DATA.CHK (season stats).
// The launcher keeps any number of them in <game>\_rosters\<id>\ (the two files plus
// roster.txt holding the display name) and switches by copying a set into place.
class RosterSet {
    public string Id, Name, Dir;
    public override string ToString() { return Name; }
}

static class RosterLibrary {
    // Paths inside the game folder (the one with default.xex).
    public static readonly string[] GamePaths = {
        @"data\xbox360_us\player\data\PLAYER_DATA.CHK",
        @"data\xbox360_us\player\season_data\SEASON_PLAYER_DATA.CHK",
    };
    public static string FileName(int i) { return Path.GetFileName(GamePaths[i]); }

    // SHA-256 of the two official rosters, so they are recognised wherever they come from.
    const string OriginalPlayer = "A7F1B123C5D7D351FB24D07086EDDA131CD6150D5CBDC249274D0C2C277D1BC7";
    const string OriginalSeason = "14C3B66A8FEF514FA902181E30264E212DFE7AC21F06398FA881F819B5DA7DE8";
    const string Oct2011Player  = "F213D9CBD494881E1795A8C26255214046A4C98B3CDF2D20B0EEB565A106D193";
    const string Oct2011Season  = "215A6DF6BD8AC71DFA51023385B2B3C81DA442C2FD6D2A177FC2D02D299A4B85";
    public const string OriginalName = "2011 Opening Day (original)";
    public const string Oct2011Name  = "2011 End of season (Oct 2011 update)";

    static string Root(string data) { return Path.Combine(data, "_rosters"); }

    static string Sha(byte[] b) {
        using (var h = System.Security.Cryptography.SHA256.Create())
            return BitConverter.ToString(h.ComputeHash(b)).Replace("-", "");
    }

    // Which official roster a pair of files is, if any.
    static string Known(byte[] player, byte[] season, out string name) {
        string p = Sha(player), s = Sha(season);
        if (p == OriginalPlayer && s == OriginalSeason) { name = OriginalName; return "original"; }
        if (p == Oct2011Player && s == Oct2011Season) { name = Oct2011Name; return "oct2011"; }
        name = null; return null;
    }

    static byte[][] ReadGame(string data) {
        return new[] { File.ReadAllBytes(Path.Combine(data, GamePaths[0])),
                       File.ReadAllBytes(Path.Combine(data, GamePaths[1])) };
    }

    static bool Same(byte[] a, byte[] b) {
        if (a.Length != b.Length) return false;
        for (int i = 0; i < a.Length; i++) if (a[i] != b[i]) return false;
        return true;
    }

    static RosterSet Save(string data, string id, string name, byte[][] files) {
        string dir = Path.Combine(Root(data), id);
        Directory.CreateDirectory(dir);
        for (int i = 0; i < 2; i++) File.WriteAllBytes(Path.Combine(dir, FileName(i)), files[i]);
        File.WriteAllText(Path.Combine(dir, "roster.txt"), "name=" + name + "\r\n");
        return new RosterSet { Id = id, Name = name, Dir = dir };
    }

    static string UniqueId(string data, string baseId) {
        string id = baseId; int n = 2;
        while (Directory.Exists(Path.Combine(Root(data), id))) id = baseId + "-" + n++;
        return id;
    }

    static string Slug(string name) {
        var sb = new StringBuilder();
        foreach (char c in name.ToLowerInvariant())
            sb.Append(char.IsLetterOrDigit(c) ? c : '-');
        string s = Regex.Replace(sb.ToString(), "-+", "-").Trim('-');
        return s.Length == 0 ? "roster" : (s.Length > 40 ? s.Substring(0, 40) : s);
    }

    // Seeds the library from what is already on disk: the disc rosters (also from the old
    // _roster_backup folder) and whatever roster the game folder holds right now, so
    // nothing is lost when switching.
    static void Seed(string data) {
        Directory.CreateDirectory(Root(data));
        var sources = new List<byte[][]>();
        string legacy = Path.Combine(data, "_roster_backup");
        if (File.Exists(Path.Combine(legacy, FileName(0))) && File.Exists(Path.Combine(legacy, FileName(1))))
            sources.Add(new[] { File.ReadAllBytes(Path.Combine(legacy, FileName(0))),
                                File.ReadAllBytes(Path.Combine(legacy, FileName(1))) });
        sources.Add(ReadGame(data));
        var have = List(data, false);
        foreach (var files in sources) {
            bool stored = false;
            foreach (var s in have) if (Matches(s, files)) { stored = true; break; }
            if (stored) continue;
            string name, id = Known(files[0], files[1], out name);
            if (id == null) { id = UniqueId(data, "custom"); name = "Custom roster (saved " + DateTime.Now.ToString("yyyy-MM-dd") + ")"; }
            else if (Directory.Exists(Path.Combine(Root(data), id))) continue;
            have.Add(Save(data, id, name, files));
        }
    }

    static bool Matches(RosterSet s, byte[][] files) {
        try {
            return Same(File.ReadAllBytes(Path.Combine(s.Dir, FileName(0))), files[0])
                && Same(File.ReadAllBytes(Path.Combine(s.Dir, FileName(1))), files[1]);
        } catch { return false; }
    }

    public static List<RosterSet> List(string data) { return List(data, true); }

    static List<RosterSet> List(string data, bool seed) {
        if (seed) Seed(data);
        var result = new List<RosterSet>();
        if (!Directory.Exists(Root(data))) return result;
        foreach (string dir in Directory.GetDirectories(Root(data))) {
            if (!File.Exists(Path.Combine(dir, FileName(0))) || !File.Exists(Path.Combine(dir, FileName(1)))) continue;
            string name = Path.GetFileName(dir);
            try {
                foreach (string ln in File.ReadAllLines(Path.Combine(dir, "roster.txt")))
                    if (ln.StartsWith("name=")) name = ln.Substring(5).Trim();
            } catch { }
            result.Add(new RosterSet { Id = Path.GetFileName(dir), Name = name, Dir = dir });
        }
        // Official rosters first, then the rest by name.
        result.Sort((a, b) => {
            int ra = a.Id == "original" ? 0 : a.Id == "oct2011" ? 1 : 2;
            int rb = b.Id == "original" ? 0 : b.Id == "oct2011" ? 1 : 2;
            return ra != rb ? ra - rb : string.Compare(a.Name, b.Name, StringComparison.OrdinalIgnoreCase);
        });
        return result;
    }

    public static RosterSet Active(string data, List<RosterSet> sets) {
        try {
            var cur = ReadGame(data);
            foreach (var s in sets) if (Matches(s, cur)) return s;
        } catch { }
        return null;
    }

    // Copies a roster into the game folder and into the game's saves (which keep their own
    // copy of the player records). Returns null on success.
    public static string Activate(string data, RosterSet set) {
        try {
            if (System.Diagnostics.Process.GetProcessesByName("bobbleheadpros").Length > 0)
                return "Close MLB Bobblehead Pros first: it rewrites its save when it exits,\nwhich would undo the roster switch.";
            byte[] player = File.ReadAllBytes(Path.Combine(set.Dir, FileName(0)));
            string err = SaveRoster.Check();
            if (err != null) return err;
            Seed(data);   // keep whatever is in the folder now
            for (int i = 0; i < 2; i++)
                File.Copy(Path.Combine(set.Dir, FileName(i)), Path.Combine(data, GamePaths[i]), true);
            return SaveRoster.Apply(player);
        } catch (Exception ex) { return "Could not switch rosters:\n" + ex.Message; }
    }

    // Adds the roster from an official update package (STFS). Returns null on success.
    public static string ImportPackage(string data, string package, out RosterSet added) {
        added = null;
        byte[][] files; string err = RosterUpdate.Extract(package, out files);
        if (err != null) return err;
        return Add(data, files, null, out added);
    }

    // Adds a roster from a folder holding PLAYER_DATA.CHK and SEASON_PLAYER_DATA.CHK
    // (named by its roster.txt when it has one, else by the given name).
    public static string ImportFolder(string data, string folder, string name, out RosterSet added) {
        added = null;
        try {
            string txt = Path.Combine(folder, "roster.txt");
            if (File.Exists(txt))
                foreach (string ln in File.ReadAllLines(txt))
                    if (ln.StartsWith("name=") && ln.Length > 5) name = ln.Substring(5).Trim();
        } catch { }
        var files = new byte[2][];
        for (int i = 0; i < 2; i++) {
            string p = Path.Combine(folder, FileName(i));
            if (!File.Exists(p)) return "That folder has no " + FileName(i) + ".";
            files[i] = File.ReadAllBytes(p);
            if (files[i].Length < 4 || Encoding.ASCII.GetString(files[i], 0, 4) != "CHK ")
                return FileName(i) + " is not a roster file.";
        }
        return Add(data, files, name, out added);
    }

    static string Add(string data, byte[][] files, string name, out RosterSet added) {
        added = null;
        try {
            foreach (var s in List(data)) if (Matches(s, files)) { added = s; return null; }
            string known, id = Known(files[0], files[1], out known);
            if (id == null) {
                if (string.IsNullOrEmpty(name)) name = "Custom roster";
                id = UniqueId(data, Slug(name));
            } else name = known;
            added = Save(data, id, name, files);
            return null;
        } catch (Exception ex) { return "Could not add the roster:\n" + ex.Message; }
    }
}

// The game copies the player records into its save when the save is created and from then
// on reads names, ratings and looks from the save; only the team table comes from
// PLAYER_DATA.CHK. So a roster switch also writes the records into every Pros save:
// all 1300 slots at 0x805C0, then a 25-record list the game fills with the first 25.
static class SaveRoster {
    const int Records = 0x805C0, Slots = 1300, Stride = 280, Extra = 25, Rec0 = 0x20;

    public static string RootOverride;   // tests only
    static string Root {
        get { return RootOverride ?? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "bobbleheadpros"); }
    }

    // Every Pros save: <root>\<profile>\58410B7B\00000001\<name>\savedata1
    static List<string> Saves() {
        var list = new List<string>();
        if (!Directory.Exists(Root)) return list;
        foreach (string f in Directory.GetFiles(Root, "savedata1", SearchOption.AllDirectories))
            if (f.IndexOf(@"\58410B7B\00000001\", StringComparison.OrdinalIgnoreCase) >= 0
                && f.IndexOf(@"\_save_backups\", StringComparison.OrdinalIgnoreCase) < 0)
                list.Add(f);
        return list;
    }

    static int U16(byte[] b, int o) { return b[o] << 8 | b[o + 1]; }

    static bool Layout(byte[] s) {
        int end = Records + Slots * Stride, extraEnd = end + Extra * Stride;
        if (s.Length < extraEnd + Stride) return false;
        if (U16(s, Records) != 1 || U16(s, end - Stride) != 0 || U16(s, end) != 1) return false;
        for (int i = extraEnd; i < extraEnd + Stride; i++) if (s[i] != 0) return false;
        return true;
    }

    // null when every save can take a roster, else a message.
    public static string Check() {
        foreach (string f in Saves())
            if (!Layout(File.ReadAllBytes(f)))
                return "A Pros save has an unexpected layout, so the roster was not switched:\n" + f;
        return null;
    }

    public static string Apply(byte[] player) {
        try {
            string backups = Path.Combine(Root, "_save_backups");
            foreach (string f in Saves()) {
                byte[] s = File.ReadAllBytes(f);
                if (!Layout(s)) return "Skipped a save with an unexpected layout:\n" + f;
                // one backup per save, from before the first roster switch; never overwritten
                Directory.CreateDirectory(backups);
                string rel = f.Substring(Root.Length).Trim('\\').Replace('\\', '_');
                string bak = Path.Combine(backups, rel + ".original");
                if (!File.Exists(bak)) File.Copy(f, bak);
                Buffer.BlockCopy(player, Rec0, s, Records, Slots * Stride);
                Buffer.BlockCopy(player, Rec0, s, Records + Slots * Stride, Extra * Stride);
                string tmp = f + ".tmp";
                File.WriteAllBytes(tmp, s);
                File.Copy(tmp, f, true);
                File.Delete(tmp);
            }
            return null;
        } catch (Exception ex) { return "The roster files were switched, but a save could not be updated:\n" + ex.Message; }
    }
}

// Reads the two roster files out of the Oct 2011 roster update package (an Xbox 360
// STFS file, "MLB Bobblehead Pros - Roster Update Oct.11"). The game never mounts the
// package itself; the launcher installs its contents instead (see RosterLibrary).
static class RosterUpdate {
    const uint TitleId = 0x58410B7B;
    const int Block = 0x1000;
    static readonly string[] PackagePaths = {
        "data/xbox360_us/player/data/PLAYER_DATA_OCT2011.CHK",
        "data/xbox360_us/player/season_data/SEASON_PLAYER_DATA_OCT2011.CHK",
    };

    // Returns null on success (files = PLAYER_DATA, SEASON_PLAYER_DATA), else a message.
    public static string Extract(string package, out byte[][] files) {
        files = null;
        byte[] pkg;
        try { pkg = File.ReadAllBytes(package); } catch (Exception ex) { return "Could not read the file:\n" + ex.Message; }
        if (pkg.Length < 0x3000) return "That file is too small to be an Xbox 360 content package.";
        string magic = Encoding.ASCII.GetString(pkg, 0, 4);
        if (magic != "CON " && magic != "LIVE" && magic != "PIRS")
            return "That is not an Xbox 360 content package (STFS).\n\n"
                 + "If you have the .7z download, extract it first and choose the file inside\n"
                 + "58410B7B\\00000002\\.";
        if (BE32(pkg, 0x360) != TitleId) return "That package is for a different game (not MLB Bobblehead Pros).";

        var entries = ReadFileTable(pkg);
        if (entries == null) return "Could not read the package's file table.";
        var found = new byte[PackagePaths.Length][];
        for (int i = 0; i < PackagePaths.Length; i++) {
            Entry e;
            if (!entries.TryGetValue(PackagePaths[i].ToUpperInvariant(), out e))
                return "This package does not contain the Oct 2011 roster update\n(missing " + PackagePaths[i] + ").";
            byte[] bytes = ReadFile(pkg, e);
            if (bytes == null || bytes.Length < 4 || Encoding.ASCII.GetString(bytes, 0, 4) != "CHK ")
                return "The roster data in this package could not be read correctly.";
            found[i] = bytes;
        }
        files = found;
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
        string err = GameRun.Start(g);
        if (err != null)
            MessageBox.Show("Failed to launch:\n" + err, "Launcher", MessageBoxButtons.OK, MessageBoxIcon.Error);
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

// Optional launcher features, chosen at build time. The roster switcher (season rosters,
// the Oct 2011 update) is not part of the v0.1.0 release, which ships the base games only;
// build with  csc -define:ROSTERS ...  to include it.
static class Features {
#if ROSTERS
    public const bool Rosters = true;
#else
    public const bool Rosters = false;
#endif
}

class SetupForm : GradientForm {
    List<GameDef> games;
    public SetupForm(List<GameDef> g) {
        games = g;
        int height = Features.Rosters ? 400 : 300;
        Text = "Setup"; ClientSize = new Size(560, height);
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
        if (Features.Rosters && pros != null) BuildRosterRow(pros, y + 10);

        var done = new RoundButton { Text = "Done", Size = new Size(120, 42), Location = new Point(560 - 24 - 120, height - 58) };
        done.Click += delegate { Config.Save(games); Close(); };
        Controls.Add(done);
    }
    void BuildRow(GameDef gd, ref int y) {
        var name = new Label { Text = gd.Name, ForeColor = Theme.Ink, Font = new Font("Segoe UI", 11, FontStyle.Bold),
            AutoSize = true, Location = new Point(26, y), BackColor = Color.Transparent };
        Controls.Add(name);
        var status = new Label { ForeColor = gd.Installed ? Theme.Good : Theme.Bad, Font = new Font("Segoe UI", 10),
            AutoSize = true, Location = new Point(300, y + 1), BackColor = Color.Transparent };
        status.Text = !gd.Installed ? "Not found" : gd.XexMatches(gd.Data) ? "Verified" : "Installed";
        Controls.Add(status);
        var locate = new RoundButton { Text = "Locate folder...", Size = new Size(150, 36), Location = new Point(390, y - 4) };
        locate.Click += delegate {
            using (var fb = new FolderBrowserDialog()) {
                fb.Description = "Select the " + gd.Name + " folder (contains default.xex)";
                if (fb.ShowDialog() == DialogResult.OK) {
                    string path = fb.SelectedPath;
                    if (File.Exists(Path.Combine(path, "default.xex"))) {
                        bool ok = gd.XexMatches(path);
                        Logs.Write("setup " + gd.Key + ": located " + path + " (default.xex " + (ok ? "verified" : "does NOT match the expected version") + ")");
                        if (!ok && MessageBox.Show(
                                "This default.xex is not the version " + gd.Name + " was built from.\n\n" +
                                "It may be a different region or version, or the files may have been modified. " +
                                "These builds were made from the Xbox Live Arcade release (World) and only " +
                                "work with that exact default.xex.\n\nUse this folder anyway?",
                                "Setup", MessageBoxButtons.YesNo, MessageBoxIcon.Warning, MessageBoxDefaultButton.Button2)
                            != DialogResult.Yes)
                            return;
                        gd.Data = path;
                        status.ForeColor = gd.Installed ? (ok ? Theme.Good : Theme.Bad) : Theme.Bad;
                        status.Text = !gd.Installed ? "Exe missing" : ok ? "Verified" : "Unverified copy";
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
        var name = new Label { Text = "Pros roster", ForeColor = Theme.Ink,
            Font = new Font("Segoe UI", 11, FontStyle.Bold), AutoSize = true, Location = new Point(26, y),
            BackColor = Color.Transparent };
        Controls.Add(name);
        var pick = new ComboBox { DropDownStyle = ComboBoxStyle.DropDownList, Location = new Point(28, y + 30),
            Width = 340, Font = new Font("Segoe UI", 10) };
        Controls.Add(pick);
        var status = new Label { Font = new Font("Segoe UI", 9), AutoSize = true, Location = new Point(28, y + 62),
            BackColor = Color.Transparent, ForeColor = Theme.Muted };
        Controls.Add(status);

        bool filling = false;
        Action refresh = delegate {
            filling = true;
            pick.Items.Clear();
            if (!pros.Installed) {
                pick.Enabled = false; status.ForeColor = Theme.Muted;
                status.Text = "Locate the Pros folder first."; filling = false; return;
            }
            try {
                var sets = RosterLibrary.List(pros.Data);
                foreach (var s in sets) pick.Items.Add(s);
                var active = RosterLibrary.Active(pros.Data, sets);
                if (active != null) pick.SelectedIndex = sets.FindIndex(s => s.Id == active.Id);
                pick.Enabled = sets.Count > 0;
                status.ForeColor = Theme.Good;
                status.Text = active != null ? "In use: " + active.Name : "The game folder's roster isn't in the library.";
            } catch (Exception ex) {
                pick.Enabled = false; status.ForeColor = Theme.Bad; status.Text = "Rosters unavailable: " + ex.Message;
            }
            filling = false;
        };
        refresh();

        pick.SelectedIndexChanged += delegate {
            if (filling) return;
            var set = pick.SelectedItem as RosterSet;
            if (set == null) return;
            string err = RosterLibrary.Activate(pros.Data, set);
            if (err != null) MessageBox.Show(err, "Rosters", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            refresh();
        };

        var import = new RoundButton { Text = "Import...", Size = new Size(150, 36), Location = new Point(390, y + 26) };
        var menu = new ContextMenuStrip();
        menu.Items.Add("Roster update package (Oct 2011)...", null, delegate {
            using (var ofd = new OpenFileDialog()) {
                ofd.Title = "Choose the roster update package (inside 58410B7B\\00000002\\ of the extracted download)";
                ofd.Filter = "Xbox 360 content package (*.*)|*.*";
                if (ofd.ShowDialog() != DialogResult.OK) return;
                RosterSet added; string err = RosterLibrary.ImportPackage(pros.Data, ofd.FileName, out added);
                Finish(err, added, pros, refresh);
            }
        });
        menu.Items.Add("Roster folder (PLAYER_DATA.CHK + SEASON_PLAYER_DATA.CHK)...", null, delegate {
            using (var fb = new FolderBrowserDialog()) {
                fb.Description = "Select a folder containing PLAYER_DATA.CHK and SEASON_PLAYER_DATA.CHK";
                if (fb.ShowDialog() != DialogResult.OK) return;
                string label = Path.GetFileName(fb.SelectedPath.TrimEnd('\\'));
                RosterSet added; string err = RosterLibrary.ImportFolder(pros.Data, fb.SelectedPath, label, out added);
                Finish(err, added, pros, refresh);
            }
        });
        import.Click += delegate {
            if (!pros.Installed) { MessageBox.Show("Locate the MLB Bobblehead Pros folder first.", "Rosters"); return; }
            menu.Show(import, new Point(0, import.Height));
        };
        Controls.Add(import);
    }

    // After an import: offer to switch to the new roster right away.
    static void Finish(string err, RosterSet added, GameDef pros, Action refresh) {
        if (err != null) { MessageBox.Show(err, "Rosters", MessageBoxButtons.OK, MessageBoxIcon.Warning); return; }
        if (MessageBox.Show("Added \"" + added.Name + "\".\nUse it now?", "Rosters",
                MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes) {
            string e2 = RosterLibrary.Activate(pros.Data, added);
            if (e2 != null) MessageBox.Show(e2, "Rosters", MessageBoxButtons.OK, MessageBoxIcon.Warning);
        }
        refresh();
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

static class AppInfo {
    public const string Version = "0.1.0";   // keep in step with installer\build-installer.ps1
    public const string IssuesUrl = "https://github.com/Wndwsqrrl/MLBBobble-recomp/issues";
}

// Logs live in Documents\bobbleheadpros\logs, next to the saves: the games' own folder
// may be under Program Files, where they cannot write. The launcher gives each game
// session its own log file (keeping the last 10 per game) and keeps a launcher.log.
static class Logs {
    public static string DirOverride;   // tests only
    public static string Dir {
        get { return DirOverride ?? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "bobbleheadpros", "logs"); }
    }
    public static string LauncherLog { get { return Path.Combine(Dir, "launcher.log"); } }

    public static void Write(string message) {
        try {
            Directory.CreateDirectory(Dir);
            var fi = new FileInfo(LauncherLog);
            if (fi.Exists && fi.Length > 1024 * 1024) {             // keep one previous file
                string old = Path.Combine(Dir, "launcher.old.log");
                if (File.Exists(old)) File.Delete(old);
                File.Move(LauncherLog, old);
            }
            File.AppendAllText(LauncherLog, DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + "  " + message + "\r\n");
        } catch { }
    }

    // A fresh log path for one game session; older sessions beyond the last 10 are removed.
    public static string NewGameLog(string key) {
        try {
            Directory.CreateDirectory(Dir);
            var old = new List<FileInfo>(new DirectoryInfo(Dir).GetFiles(key + "_*.log"));
            old.Sort((a, b) => b.LastWriteTime.CompareTo(a.LastWriteTime));
            for (int i = 9; i < old.Count; i++) { try { old[i].Delete(); } catch { } }
        } catch { }
        return Path.Combine(Dir, key + "_" + DateTime.Now.ToString("yyyyMMdd-HHmmss") + ".log");
    }
}

static class GameRun {
    // Starts a game with its data folder and a log file. Returns null on success.
    public static string Start(GameDef g) {
        try {
            string log = Logs.NewGameLog(g.Key);
            string args = "--game_data_root=\"" + g.Data + "\" --log_file=\"" + log + "\"";
            var psi = new ProcessStartInfo(g.Exe, args);
            psi.WorkingDirectory = Path.GetDirectoryName(g.Exe);
            psi.UseShellExecute = true;
            Process.Start(psi);
            Logs.Write("start " + g.Key + ": \"" + g.Exe + "\" " + args);
            return null;
        } catch (Exception ex) {
            Logs.Write("start " + g.Key + " FAILED: " + ex.Message);
            return ex.Message;
        }
    }
}

// "Report a problem": one zip on the Desktop with what is needed to look into an issue:
// recent game logs, the launcher log, a short system summary and both games' settings.
// The user's Windows account name is replaced with <user> in everything collected.
static class Report {
    [System.Runtime.InteropServices.StructLayout(System.Runtime.InteropServices.LayoutKind.Sequential)]
    class MEMORYSTATUSEX {
        public uint dwLength = 64, dwMemoryLoad;
        public ulong ullTotalPhys, ullAvailPhys, ullTotalPageFile, ullAvailPageFile, ullTotalVirtual, ullAvailVirtual, ullAvailExtendedVirtual;
    }
    [System.Runtime.InteropServices.DllImport("kernel32.dll")]
    static extern bool GlobalMemoryStatusEx([System.Runtime.InteropServices.In, System.Runtime.InteropServices.Out] MEMORYSTATUSEX m);

    static string Reg(string key, string name) {
        try { var v = Microsoft.Win32.Registry.GetValue(key, name, null); return v == null ? "?" : v.ToString().Trim(); }
        catch { return "?"; }
    }

    static string Clean(string text) {
        string profile = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
        if (!string.IsNullOrEmpty(profile)) text = Regex.Replace(text, Regex.Escape(profile), "<user-folder>", RegexOptions.IgnoreCase);
        string user = Environment.UserName;
        if (!string.IsNullOrEmpty(user) && user.Length > 1)
            text = Regex.Replace(text, @"(?<![A-Za-z0-9])" + Regex.Escape(user) + @"(?![A-Za-z0-9])", "<user>", RegexOptions.IgnoreCase);
        return text;
    }

    public static string SystemSummary(List<GameDef> games) {
        var sb = new StringBuilder();
        sb.AppendLine("MLB Bobblehead Recomp launcher " + AppInfo.Version);
        sb.AppendLine("Report created: " + DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"));
        const string nt = @"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion";
        // ProductName still says "Windows 10" on Windows 11; the build number tells them apart.
        string product = Reg(nt, "ProductName"); int build;
        if (int.TryParse(Reg(nt, "CurrentBuild"), out build) && build >= 22000) product = product.Replace("Windows 10", "Windows 11");
        sb.AppendLine("Windows: " + product + " " + Reg(nt, "DisplayVersion") + " (build " + Reg(nt, "CurrentBuild") + "." + Reg(nt, "UBR") + ")"
                      + (Environment.Is64BitOperatingSystem ? ", 64-bit" : ", 32-bit"));
        sb.AppendLine("CPU: " + Reg(@"HKEY_LOCAL_MACHINE\HARDWARE\DESCRIPTION\System\CentralProcessor\0", "ProcessorNameString")
                      + " (" + Environment.ProcessorCount + " threads)");
        try { var m = new MEMORYSTATUSEX(); if (GlobalMemoryStatusEx(m)) sb.AppendLine("RAM: " + (m.ullTotalPhys / (1024 * 1024 * 1024.0)).ToString("0.0") + " GB"); } catch { }
        try {
            using (var q = new System.Management.ManagementObjectSearcher("SELECT Name, DriverVersion, AdapterRAM FROM Win32_VideoController"))
                foreach (System.Management.ManagementObject o in q.Get())
                    sb.AppendLine("GPU: " + o["Name"] + ", driver " + o["DriverVersion"]);
        } catch (Exception ex) { sb.AppendLine("GPU: unknown (" + ex.Message + ")"); }
        foreach (var g in games) {
            sb.AppendLine();
            sb.AppendLine(g.Name + ":");
            sb.AppendLine("  program: " + (File.Exists(g.Exe) ? g.Exe : "missing (" + g.Exe + ")"));
            sb.AppendLine("  game folder: " + (string.IsNullOrEmpty(g.Data) ? "not set" : g.Data));
            bool hasXex = !string.IsNullOrEmpty(g.Data) && File.Exists(Path.Combine(g.Data, "default.xex"));
            sb.AppendLine("  default.xex: " + (!hasXex ? "not found" : g.XexMatches(g.Data) ? "verified (expected version)" : "DIFFERENT from the expected version"));
        }
        return Clean(sb.ToString());
    }

    public static string OutDirOverride;   // tests only

    // Returns the zip's path, or throws.
    public static string Create(List<GameDef> games) {
        string desktop = OutDirOverride ?? Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);
        string zipPath = Path.Combine(desktop, "MLB-Bobblehead-report-" + DateTime.Now.ToString("yyyyMMdd-HHmmss") + ".zip");
        using (var zip = System.IO.Compression.ZipFile.Open(zipPath, System.IO.Compression.ZipArchiveMode.Create)) {
            Action<string, string> add = (name, text) => {
                var e = zip.CreateEntry(name);
                using (var w = new StreamWriter(e.Open(), new UTF8Encoding(false))) w.Write(text);
            };
            add("system.txt", SystemSummary(games));
            Func<string, string> read = p => {
                using (var fs = new FileStream(p, FileMode.Open, FileAccess.Read, FileShare.ReadWrite))   // a running game keeps its log open
                using (var r = new StreamReader(fs)) return Clean(r.ReadToEnd());
            };
            if (Directory.Exists(Logs.Dir)) {
                foreach (var g in games) {
                    var logs = new List<FileInfo>(new DirectoryInfo(Logs.Dir).GetFiles(g.Key + "_*.log"));
                    logs.Sort((a, b) => b.LastWriteTime.CompareTo(a.LastWriteTime));
                    for (int i = 0; i < Math.Min(3, logs.Count); i++)
                        try { add("logs/" + logs[i].Name, read(logs[i].FullName)); } catch { }
                }
                foreach (string n in new[] { "launcher.log", "launcher.old.log" })
                    if (File.Exists(Path.Combine(Logs.Dir, n))) try { add("logs/" + n, read(Path.Combine(Logs.Dir, n))); } catch { }
            }
            foreach (var g in games) {
                try {
                    string toml = Path.ChangeExtension(g.Exe, ".toml");
                    if (File.Exists(toml)) add("settings/" + Path.GetFileName(toml), read(toml));
                } catch { }
            }
        }
        Logs.Write("report created: " + Clean(zipPath));
        return zipPath;
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
                XexSha = "978423F1AFF4507D62D867D7839F816C407E8A500F2B15B98DD3145D79CFCCE5",
                Icons = new[] { Path.Combine(artDir, "pros.png"),
                                string.IsNullOrEmpty(prosData) ? "" : Path.Combine(prosData, "TitleIcon.png") } },
            new GameDef { Key = "battle", Name = "MLB Bobblehead Battle",
                Exe = battleExe, Data = battleData,
                XexSha = "1ADA5B978D047429A138AC68505C62D5101E96DF5B260C6003106DCE88B36E1D",
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
            if (pg != null && pg.Installed && GameRun.Start(pg) == null) return;
            // otherwise fall through to the launcher window
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

        var report = new RoundButton { Text = "Report a problem", Size = new Size(170, 36),
            Location = new Point(w - margin - 170, 28) };
        report.Click += delegate {
            try {
                string zip = Report.Create(games);
                Process.Start("explorer.exe", "/select,\"" + zip + "\"");
                MessageBox.Show(
                    "A problem report was saved to your Desktop:\n" + Path.GetFileName(zip) + "\n\n" +
                    "It holds your recent game and launcher logs, a short system summary (Windows, CPU, RAM, GPU) " +
                    "and the games' settings; your Windows user name is removed. No game files are included.\n\n" +
                    "Send it in with a short description of what happened, for example by attaching it to an issue at\n" +
                    AppInfo.IssuesUrl, "Report a problem", MessageBoxButtons.OK, MessageBoxIcon.Information);
            } catch (Exception ex) {
                MessageBox.Show("Could not create the report:\n" + ex.Message, "Report a problem",
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
        };
        f.Controls.Add(report);

        Logs.Write("launcher " + AppInfo.Version + " started" + (playKey != null ? " (--play " + playKey + ")" : ""));
        Application.Run(f);
    }
}
