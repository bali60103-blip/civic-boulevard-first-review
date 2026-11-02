// Illustrator：將 _ai_layers/ 之分層 PDF（由下而上）依序置入、嵌入為向量，建立具名圖層，存成 AI
// 由 24_make_ai.sh 以 osascript 呼叫；參數寫在同目錄 ai_job.json
#target illustrator
(function () {
    app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
    var jobFile = new File($.fileName.replace(/[^\/]+$/, '') + 'ai_job.json');
    jobFile.encoding = 'UTF-8'; jobFile.open('r'); var job = eval('(' + jobFile.read() + ')'); jobFile.close();
    var pt = 72 / 25.4;
    var doc = app.documents.add(DocumentColorSpace.RGB, job.w_mm * pt, job.h_mm * pt);
    app.preferences.PDFFileOptions.pDFCropToBox = PDFBoxType.PDFMEDIABOX;
    var ab = doc.artboards[0].artboardRect;           // [left, top, right, bottom]
    var base = doc.layers[0];
    var log = [];
    for (var i = 0; i < job.layers.length; i++) {       // 由下而上：layers.add() 新圖層置頂
        var L = doc.layers.add(); L.name = job.layers[i][0];
        var p = L.placedItems.add(); p.file = new File(job.layers[i][1]);
        p.position = [ab[0], ab[1]];
        p.embed();
        log.push(L.name + ' | items ' + L.pageItems.length);
    }
    base.remove();
    var o = new IllustratorSaveOptions(); o.pdfCompatible = true; o.embedLinkedFiles = true;
    var target = new File(job.out), note = 'none';
    for (var k = app.documents.length - 1; k >= 0; k--) {          // 同名檔已開啟：避免舊視窗日後覆蓋新檔
        var od = app.documents[k]; if (od === doc) continue;
        try { if (od.fullName.fsName == target.fsName) {
            if (od.saved) { od.close(SaveOptions.DONOTSAVECHANGES); note = 'closed stale window'; }
            else { target = new File(job.out.replace(/\.ai$/, '_新版.ai')); note = 'UNSAVED edits open in Illustrator; saved as ' + target.name; }
        } } catch (e) {}
    }
    doc.saveAs(target, o);
    log.push('note: ' + note);
    // 檢核：圖層名稱（由上而下）
    var names = []; for (var j = 0; j < doc.layers.length; j++) names.push(doc.layers[j].name);
    var lf = new File(job.log); lf.encoding = 'UTF-8'; lf.open('w'); lf.write(log.join('\n') + '\n---\n' + names.join('\n')); lf.close();
    doc.close(SaveOptions.DONOTSAVECHANGES);
})();
