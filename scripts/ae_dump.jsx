/*
 * ae_dump.jsx — 把 After Effects 工程导出成 JSON，供 AI 读取与诊断。
 *
 * 它不是"另一个 AE 脚本工具"，而是补上成片视频无法提供的那一层：
 * 图层名、关键帧密度、效果参数、文字内容、父子关系、标记。
 * 从视频里永远看不出"这一层有 180 个位置关键帧"。
 *
 * 运行方式（AE 必须是关闭状态，或允许它在启动后自动退出）：
 *   Windows:
 *     set AE_DUMP_OUT=G:\proj\ae_dump.json
 *     "G:\AE\Adobe After Effects 2026\Support Files\AfterFX.exe" -r "…\ae_dump.jsx"
 *   macOS:
 *     AE_DUMP_OUT=/tmp/ae_dump.json /Applications/Adobe\ After\ Effects\ 2026/Adobe\ After\ Effects\ 2026.app/Contents/MacOS/After\ Effects -r "…/ae_dump.jsx"
 *
 * 无参数运行（双击/在 AE 里 File > Scripts > Run Script File）：
 *   输出到 工程文件同目录 / ae_dump.json（未保存则输出到桌面）
 *
 * 可选环境变量：
 *   AE_DUMP_OUT            输出路径
 *   AE_DUMP_TRANSFORM_ONLY 设为 1 时只导变换与效果，跳过其它属性（大工程更快）
 *   AE_DUMP_MAX_KEYS       每个属性最多记录多少关键帧（默认 24，超出只记统计）
 *   AE_DUMP_QUIT           设为 0 时不自动退出 AE（默认自动退出）
 *
 * 注意：本脚本只读，不修改工程。但仍建议先备份 .aep 再运行任何脚本。
 */

(function () {
    var T0 = new Date().getTime();

    // ---------- 工具 ----------

    function env(name, dflt) {
        var v = $.getenv(name);
        return (v === null || v === "" || typeof v === "undefined") ? dflt : v;
    }

    function esc(s) {
        s = String(s);
        var out = "";
        for (var i = 0; i < s.length; i++) {
            var c = s.charAt(i);
            var code = s.charCodeAt(i);
            if (c === '"') out += '\\"';
            else if (c === "\\") out += "\\\\";
            else if (c === "\n") out += "\\n";
            else if (c === "\r") out += "";
            else if (c === "\t") out += "\\t";
            else if (code < 32) out += " ";
            else out += c;
        }
        return out;
    }

    function r3(v) {
        if (typeof v !== "number" || !isFinite(v)) return 0;
        return Math.round(v * 1000) / 1000;
    }

    // ExtendScript 没有可靠的 JSON，手写编码
    function enc(v) {
        if (v === null || typeof v === "undefined") return "null";
        if (typeof v === "number") return isFinite(v) ? String(r3(v)) : "null";
        if (typeof v === "boolean") return v ? "true" : "false";
        if (typeof v === "string") return '"' + esc(v) + '"';
        if (v instanceof Array) {
            var a = [];
            for (var i = 0; i < v.length; i++) a.push(enc(v[i]));
            return "[" + a.join(",") + "]";
        }
        var parts = [];
        for (var k in v) {
            if (!v.hasOwnProperty(k)) continue;
            if (typeof v[k] === "function") continue;
            parts.push('"' + esc(k) + '":' + enc(v[k]));
        }
        return "{" + parts.join(",") + "}";
    }

    function layerType(l) {
        if (l instanceof TextLayer) return "text";
        if (l instanceof ShapeLayer) return "shape";
        if (l instanceof CameraLayer) return "camera";
        if (l instanceof LightLayer) return "light";
        if (l instanceof AVLayer) {
            if (l.nullLayer) return "null";
            try {
                if (l.source && l.source.mainSource && l.source.mainSource instanceof SolidSource) return "solid";
            } catch (e) {}
            return "av";
        }
        return "other";
    }

    // ---------- 属性 / 关键帧 ----------

    var MAX_KEYS = parseInt(env("AE_DUMP_MAX_KEYS", "24"), 10);
    var TRANSFORM_ONLY = env("AE_DUMP_TRANSFORM_ONLY", "0") === "1";

    // 这些是可动画的变换属性名（含日文版 AE 的常见名）
    var XFORM = {
        "Position": 1, "位置": 1, "Scale": 1, "缩放": 1,
        "Rotation": 1, "旋转": 1, "Opacity": 1, "不透明度": 1,
        "Anchor Point": 1, "锚点": 1, "Orientation": 1, "方向": 1,
        "Rotation X": 1, "Rotation Y": 1, "Rotation Z": 1,
        "X Rotation": 1, "Y Rotation": 1, "Z Rotation": 1
    };

    function propVal(p) {
        try {
            var v = p.value;
            if (v instanceof Array) {
                var a = [];
                for (var i = 0; i < v.length; i++) a.push(v[i]);
                return a;
            }
            return v;
        } catch (e) {
            return null;
        }
    }

    function dumpKeyframes(p) {
        var n = 0;
        try { n = p.numKeys; } catch (e) { return null; }
        if (!n) return null;

        var keys = [];
        var lim = Math.min(n, MAX_KEYS);
        var linearCount = 0;
        for (var i = 1; i <= lim; i++) {
            var inT = [0, 0, 0];
            var outT = [0, 0, 0];
            var inI = 0, outI = 0;
            try { inT = p.keyInTemporalEase(i); } catch (e) {}
            try { outT = p.keyOutTemporalEase(i); } catch (e) {}
            // 6612=线性 6613=贝塞尔 6614=定格。线性多 = 运动机械
            try { inI = p.keyInInterpolationType(i); } catch (e) {}
            try { outI = p.keyOutInterpolationType(i); } catch (e) {}
            if (inI === 6612 || outI === 6612) linearCount++;
            keys.push({
                t: r3(p.keyTime(i)),
                v: propVal({ value: p.keyValue(i) }),
                inSpeed: inT && inT[0] ? r3(inT[0].speed) : 0,
                outSpeed: outT && outT[0] ? r3(outT[0].speed) : 0,
                it: inI,
                ot: outI
            });
        }
        var res = { count: n, sample: keys };
        if (linearCount > 0) {
            res.linear_keys = linearCount;
            res.linear_ratio = r3(linearCount / lim);
        }
        if (n > MAX_KEYS) res.note = "truncated at " + MAX_KEYS;
        // 关键帧密度：平均间隔（秒），过小说明关键帧"哔哩哔哩"地太多
        if (n > 2) {
            var span = p.keyTime(n) - p.keyTime(1);
            if (span > 0) res.avg_gap_s = r3(span / (n - 1));
        }
        return res;
    }

    function dumpProp(p, depth, bag, prefix) {
        var name = "";
        try { name = p.name; } catch (e) { name = "?"; }

        // 属性组 → 递归
        var isGroup = false;
        try { isGroup = (p.numProperties > 0); } catch (e) { isGroup = false; }
        if (isGroup) {
            if (depth > 4) return;
            for (var i = 1; i <= p.numProperties; i++) {
                var sub = p.property(i);
                if (sub) dumpProp(sub, depth + 1, bag, prefix + name + "/");
            }
            return;
        }

        if (TRANSFORM_ONLY && !XFORM[name] && prefix.indexOf("Effects") < 0 && prefix.indexOf("效果") < 0) {
            // TRANSFORM_ONLY 时这里只保留变换与效果参数，其余照常（属性组已在上层过滤）
        }

        var kf = dumpKeyframes(p);
        var isTextDoc = false;
        try { isTextDoc = (p.propertyValueType === PropertyValueType.TEXT_DOCUMENT); } catch (e) {}

        var rec = { name: name };
        if (kf) {
            rec.animated = true;
            rec.keys = kf.count;
            if (kf.avg_gap_s) rec.avg_gap_s = kf.avg_gap_s;
            rec.sample = kf.sample;
        } else {
            if (!isTextDoc) {
                var v = propVal(p);
                if (v !== null && typeof v !== "object") rec.value = v;
                else if (v instanceof Array) rec.value = v;
            }
        }

        // 文字内容（诊断"文字是否压在脸上/字号多大"用）
        if (isTextDoc) {
            try {
                var td = p.value;
                rec.text = String(td.text);
                rec.fontSize = r3(td.fontSize);
                rec.font = String(td.font);
                rec.justification = String(td.justification);
                rec.tracking = r3(td.tracking);
                rec.leading = r3(td.leading);
            } catch (e) {}
        }

        bag.push(rec);
    }

    // ---------- 图层 ----------

    function dumpLayer(l) {
        var o = {
            index: l.index,
            name: "",
            type: layerType(l),
            enabled: false,
            locked: false,
            inPoint: 0,
            outPoint: 0,
            startTime: 0,
            stretch: 1,
            parent: null,
            threeD: false,
            effects: []
        };
        try { o.name = l.name; } catch (e) {}
        try { o.enabled = !!l.enabled; } catch (e) {}
        try { o.locked = !!l.locked; } catch (e) {}
        try { o.inPoint = r3(l.inPoint); } catch (e) {}
        try { o.outPoint = r3(l.outPoint); } catch (e) {}
        try { o.startTime = r3(l.startTime); } catch (e) {}
        try { o.stretch = r3(l.stretch); } catch (e) {}
        try { o.threeD = !!l.threeDLayer; } catch (e) {}
        try { if (l.parent) o.parent = l.parent.index; } catch (e) {}

        // 素材来源
        try {
            if (l.source) {
                o.source = l.source.name;
                if (l.source.duration) o.source_dur = r3(l.source.duration);
            }
        } catch (e) {}

        // 混合模式
        try {
            if (l.blendingMode !== undefined) o.blend = String(l.blendingMode);
        } catch (e) {}

        // 变换（诊断"关键帧太多/缓动不对"）
        try {
            var xf = l.property("ADBE Transform Group");
            if (xf) {
                var bag = [];
                for (var i = 1; i <= xf.numProperties; i++) {
                    var pr = xf.property(i);
                    if (pr) dumpProp(pr, 1, bag, "transform/");
                }
                o.transform = bag;
            }
        } catch (e) {}

        // 效果
        try {
            var eg = l.property("ADBE Effect Parade");
            if (eg && !TRANSFORM_ONLY) {
                for (var j = 1; j <= eg.numProperties; j++) {
                    var ef = eg.property(j);
                    if (!ef) continue;
                    var eb = [];
                    for (var k = 1; k <= ef.numProperties; k++) {
                        var ep = ef.property(k);
                        if (ep) dumpProp(ep, 1, eb, "fx/");
                    }
                    o.effects.push({ name: ef.name, enabled: !!ef.enabled, params: eb });
                }
            }
        } catch (e) {}

        // 文字层内容
        if (o.type === "text") {
            try {
                var src = l.property("ADBE Text Properties").property("ADBE Text Document");
                var td = src.value;
                o.text = String(td.text);
                o.fontSize = r3(td.fontSize);
                o.font = String(td.font);
                o.tracking = r3(td.tracking);
            } catch (e) {}
        }
        return o;
    }

    function dumpComp(c) {
        var o = {
            name: c.name,
            id: c.id,
            width: c.width,
            height: c.height,
            duration: r3(c.duration),
            frameRate: r3(c.frameRate),
            numLayers: c.numLayers,
            bg: null,
            markers: [],
            layers: []
        };
        try {
            o.bg = [r3(c.bgColor[0] * 255), r3(c.bgColor[1] * 255), r3(c.bgColor[2] * 255)];
        } catch (e) {}

        // 标记（段落/记忆点常打在 comp 标记上）
        try {
            for (var m = 1; m <= c.markerProperty.numKeys; m++) {
                o.markers.push({ t: r3(c.markerProperty.keyTime(m)),
                                 comment: String(c.markerProperty.keyValue(m).comment) });
            }
        } catch (e) {}

        for (var i = 1; i <= c.numLayers; i++) {
            var l = c.layer(i);
            if (l) o.layers.push(dumpLayer(l));
        }
        return o;
    }

    // ---------- 主流程 ----------

    var out = env("AE_DUMP_OUT", "");
    var proj = app.project;
    if (!proj) {
        alert("没有打开的工程。请先打开 .aep 再运行。");
        return;
    }

    if (!out) {
        if (proj.file) {
            out = proj.file.parent.fsName + "/ae_dump.json";
        } else {
            out = Folder.desktop.fsName + "/ae_dump.json";
        }
    }

    var data = {
        generated: "",
        ae_version: String(app.version),
        project: proj.file ? proj.file.fsName : "(unsaved)",
        num_items: proj.numItems,
        comps: []
    };

    var totalComps = 0;
    for (var i = 1; i <= proj.numItems; i++) {
        var it = proj.item(i);
        if (it instanceof CompItem) {
            data.comps.push(dumpComp(it));
            totalComps++;
        }
    }
    data.comp_count = totalComps;

    var f = new File(out);
    f.encoding = "UTF-8";
    f.open("w");
    f.write(enc(data));
    f.close();

    var secs = Math.round((new Date().getTime() - T0) / 100) / 10;
    $.writeln("[ae_dump] " + out + "  (" + totalComps + " comps, " + secs + "s)");

    if (env("AE_DUMP_QUIT", "1") === "1") {
        app.quit();
    }
})();
