def fillProduct(db,cout):
    # так как процесс идет - продукцию берем из безопасной зоны времени - когда все дозвоны закончились
    db << 'SELECT MAX(`id`) l_id FROM `tele_production` WHERE `created` <DATE_SUB(NOW(), INTERVAL 3 MINUTE)'
    #import pdb; pdb.set_trace()
    supremumId = db.one()['l_id']
    rank = ('voice','b_1', 'b_2', 'b_3', 'b_4', 'b_5', 'b_6', 'b_7', 'b_8', 'b_9', 'b_?', 't_?', 'hs', '!answ', '!busy', '!over', '!noan', 'hm')
    
    db << 'SELECT `material_id`, COUNT(`id`) cnt FROM `tele_production` WHERE `id` <=%s AND inbound = 0 GROUP BY `material_id` HAVING COUNT(`id`)>1'
    issues = db.all(supremumId)
    for row in issues:
        cId = row['material_id']
        db << 'SELECT * FROM `tele_production` WHERE `material_id` = %s AND `id` <=%s AND inbound = 0'
        founded = db.all(cId,supremumId)
        intphone = 0
        success = 0
        ringingtime = 40
        calltime = 0
        trunk = 0
        redirected = 0
        keypress = ''
        ids = []
        rate = 999
        for currentRow in founded:
            ids.append(currentRow['id'])
            intphone =currentRow['intphone']
            trunk =currentRow['trunk']
            success = max(success,currentRow['success'])
            calltime = max(calltime,currentRow['calltime'])
            redirected = max(redirected,currentRow['redirected'])
            ringingtime = min(ringingtime,currentRow['ringingtime'])
            try:
                probe = rank.index(currentRow['keypress'])
            except LookupError:
                probe = 99
            if probe < rate:
                rate = probe
                keypress = currentRow['keypress']
                
        victim = ids.pop(0)
        db << 'UPDATE `tele_production` SET `intphone`=%s,`success`=%s,`ringingtime`=%s,`calltime`=%s,`trunk`=%s,`redirected`=%s,`keypress`=%s WHERE id = %s'
        db < (intphone,success,ringingtime,calltime,trunk,redirected,keypress,victim)
        db << 'DELETE FROM `tele_production` WHERE `id` IN(0,{})'.format(', '.join(map(str,ids)))
        db < None
        
    db << 'SELECT `intphone`, COUNT(`id`) cnt FROM `tele_production` WHERE `id` <=%s AND inbound = 1 GROUP BY `intphone` HAVING COUNT(`id`)>1'
    issues = db.all(supremumId)
    for row in issues:
        cPhone = row['intphone']
        db << 'SELECT * FROM `tele_production` WHERE `intphone` = %s AND `id` <=%s AND inbound = 1'
        founded = db.all(cPhone,supremumId)
        intphone = 0
        success = 0
        ringingtime = 40
        calltime = 0
        trunk = 0
        redirected = 0
        keypress = ''
        ids = []
        rate = 999
        for currentRow in founded:
            ids.append(currentRow['id'])
            intphone =currentRow['intphone']
            trunk =currentRow['trunk']
            success = max(success,currentRow['success'])
            calltime = max(calltime,currentRow['calltime'])
            redirected = max(redirected,currentRow['redirected'])
            ringingtime = min(ringingtime,currentRow['ringingtime'])
            try:
                probe = rank.index(currentRow['keypress'])
            except LookupError:
                probe = 99
            if probe < rate:
                rate = probe
                keypress = currentRow['keypress']
                
        victim = ids.pop(0)
        db << 'UPDATE `tele_production` SET `intphone`=%s,`success`=%s,`ringingtime`=%s,`calltime`=%s,`trunk`=%s,`redirected`=%s,`keypress`=%s WHERE id = %s'
        db < (intphone,success,ringingtime,calltime,trunk,redirected,keypress,victim)
        db << 'DELETE FROM `tele_production` WHERE `id` IN(0, {})'.format(', '.join(map(str,ids)))
        db < None
        

    db << 'SELECT * FROM `tele_production` WHERE `id` <=%s'
    [cout << row for row in db.all(supremumId)]