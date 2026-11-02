// 讀取 AI 檔之圖層結構（名稱、可見、鎖定、物件數、外框），寫入記錄檔；參數 ai_inspect.json：{src, log}
#target illustrator
(function () {
    app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
    var jf = new File($.fileName.replace(/[^\/]+$/, '') + 'ai_inspect.json'); jf.encoding = 'UTF-8'; jf.open('r');
    var job = eval('(' + jf.read() + ')'); jf.close();
    var doc = app.open(new File(job.src));
    var out = ['artboard ' + doc.artboards[0].artboardRect.join(',')];
    function walk(L, ind) {
        var vb = L.visible ? 'V' : '-', lk = L.locked ? 'L' : '-';
        var gb = '';
        try { if (L.pageItems.length) { var b = null; for (var i = 0; i < L.pageItems.length; i++) { var g = L.pageItems[i].visibleBounds;
            b = b ? [Math.min(b[0], g[0]), Math.max(b[1], g[1]), Math.max(b[2], g[2]), Math.min(b[3], g[3])] : g; } gb = b.join(','); } } catch (e) {}
        out.push(ind + L.name + ' [' + vb + lk + '] items=' + L.pageItems.length + ' paths=' + L.pathItems.length + ' groups=' + L.groupItems.length +
                 ' sub=' + L.layers.length + ' bounds=' + gb);
        for (var j = 0; j < L.layers.length; j++) walk(L.layers[j], ind + '  ');
    }
    for (var i = 0; i < doc.layers.length; i++) walk(doc.layers[i], '');
    var lf = new File(job.log); lf.encoding = 'UTF-8'; lf.lineFeed = 'Unix'; lf.open('w'); lf.write(out.join('\n')); lf.close();
    doc.close(SaveOptions.DONOTSAVECHANGES);
})();
