// Illustrator：簡報 17 頁 → 一份 AI、17 個工作區域（1920 × 1080 pt），三圖層（底色／圖／文字），各頁 PDF 置入後嵌入為向量
// 由 05_make_ai.sh 以 osascript 呼叫；參數寫在同目錄 ai_job_slides.json
#target illustrator
(function () {
    app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
    var jobFile = new File($.fileName.replace(/[^\/]+$/, '') + 'ai_job_slides.json');
    jobFile.encoding = 'UTF-8'; jobFile.open('r'); var job = eval('(' + jobFile.read() + ')'); jobFile.close();
    var W = job.w, H = job.h, GAP = 200, COLS = 4, N = job.pages;
    var doc = app.documents.add(DocumentColorSpace.RGB, W, H);
    app.preferences.PDFFileOptions.pDFCropToBox = PDFBoxType.PDFMEDIABOX;
    var ab0 = doc.artboards[0].artboardRect;            // [left, top, right, bottom]
    var rects = [ab0];
    for (var i = 1; i < N; i++) {
        var c = i % COLS, r = Math.floor(i / COLS);
        var L = ab0[0] + c * (W + GAP), T = ab0[1] - r * (H + GAP);
        doc.artboards.add([L, T, L + W, T - H]); rects.push([L, T, L + W, T - H]);
    }
    for (var i = 0; i < N; i++) doc.artboards[i].name = job.names[i];
    var base = doc.layers[0], log = [];
    for (var k = 0; k < job.layers.length; k++) {        // 由下而上
        var Ly = doc.layers.add(); Ly.name = job.layers[k][0];
        for (var i = 0; i < N; i++) {
            app.preferences.PDFFileOptions.pageToOpen = i + 1;
            var p = Ly.placedItems.add(); p.file = new File(job.layers[k][1]);
            p.position = [rects[i][0], rects[i][1]];
            p.embed();
        }
        log.push(Ly.name + ' | items ' + Ly.pageItems.length);
    }
    base.remove();
    var o = new IllustratorSaveOptions(); o.pdfCompatible = true; o.embedLinkedFiles = true;
    var target = new File(job.out), note = 'none';
    for (var j = app.documents.length - 1; j >= 0; j--) {
        var od = app.documents[j]; if (od === doc) continue;
        try { if (od.fullName.fsName == target.fsName) {
            if (od.saved) { od.close(SaveOptions.DONOTSAVECHANGES); note = 'closed stale window'; }
            else { target = new File(job.out.replace(/\.ai$/, '_新版.ai')); note = 'UNSAVED edits open in Illustrator; saved as ' + target.name; }
        } } catch (e) {}
    }
    doc.saveAs(target, o);
    log.push('artboards ' + doc.artboards.length); log.push('note: ' + note);
    var lf = new File(job.log); lf.encoding = 'UTF-8'; lf.open('w'); lf.write(log.join('\n')); lf.close();
    doc.close(SaveOptions.DONOTSAVECHANGES);
})();
