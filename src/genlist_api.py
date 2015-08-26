#!/usr/bin/env python
# -*- coding: utf-8 -*-
import codecs   # utf8 codecs
import csv      # read/write csv files
import pypandoc # convert markdown to docx/odt, etc.
import re       # regular expression
import shutil   # copy files
import sqlite3  # lightweight database
import subprocess   # execute shell commands
import sys      # system
import os
import traceback # dealing with exception
from platform import uname


# format the typesetting of names
class Genlist(object):
    def __init__(self):
        pass

    # for pyinstaller 
    # http://stackoverflow.com/questions/7674790/bundling-data-files-with-pyinstaller-onefile
    def resource_path(self, relative):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative)
        else:
            return(relative)
        return os.path.join(os.path.abspath("."), relative)

    def fmtname(self, name):
        n_split = name.split(' ')
        lenf = len(n_split)
        # typesetting
        italic_b = '*'
        italic_e = '*'
        if 'var.' in n_split:
            sub_idx = n_split.index('var.')
            fmt_name = italic_b + " ".join(str(item) for item in n_split[0:2])+ italic_e
            fmt_author = " ".join(str(item) for item in n_split[sub_idx+2:lenf])
            fmt_sub = italic_b + str(n_split[sub_idx+1]) + italic_e
            fmt_oname = fmt_name + ' var. ' + fmt_sub + ' ' + fmt_author
        elif 'subsp.' in n_split:
            sub_idx = n_split.index('subsp.')
            fmt_name = italic_b + " ".join(str(item) for item in n_split[0:2])+ italic_e
            fmt_author = " ".join(str(item) for item in n_split[sub_idx+2:lenf])
            fmt_sub = italic_b + str(n_split[sub_idx+1]) + italic_e
            fmt_oname = fmt_name + ' subsp. ' + fmt_sub + ' ' + fmt_author
        elif 'fo.' in n_split:
            sub_idx = n_split.index('fo.')
            fmt_name = italic_b + " ".join(str(item) for item in n_split[0:2])+ italic_e
            fmt_author = " ".join(str(item) for item in n_split[sub_idx+2:lenf])
            fmt_sub = italic_b + str(n_split[sub_idx+1]) + italic_e
            fmt_oname = fmt_name + ' fo. ' + fmt_sub + ' ' + fmt_author
        elif '×' in n_split:
            fmt_name = italic_b + " ".join(str(item) for item in n_split[0:3])+ italic_e
            fmt_author = " ".join(str(item) for item in n_split[3:lenf])
            fmt_oname = fmt_name + ' ' + fmt_author
        else:
            fmt_name = italic_b + " ".join(str(item) for item in n_split[0:2])+ italic_e
            fmt_author = " ".join(str(item) for item in n_split[2:lenf])
            fmt_oname = fmt_name + ' ' + fmt_author
        # 作者中訂正(ex)需使用斜體
        fmt_oname = re.sub(' ex ', ' ' + italic_b + 'ex' + italic_e + ' ', fmt_oname)
        return(fmt_oname)

    # DEPRECATED: use pypandoc package
    # convert markdown to other fileformats using pandoc
    #
    def pandocConvert(self, oformat='docx', ofile_prefix='output'):
        dpath = sys._MEIPASS
        path_to_pandoc = os.path.join(dpath, 'pandoc')
        inpfile = ofile_prefix+'.md'
        outfile = ofile_prefix+'.'+oformat
        if uname()[0] == 'Windows':
            subprocess.Popen([path_to_pandoc, '-f', 'markdown', '-t', 'docx', inpfile, '-o', outfile], shell=True)
        else:
            subprocess.Popen([path_to_pandoc, inpfile, '-o', outfile])
        
    def dbCreateTable(self, schema, dbfile):
        conn = sqlite3.connect(dbfile)
        curs = conn.cursor()
        curs.execute(schema)
        conn.close()

    def dbImportTable(self, table_name, csvfile, dbfile):
        conn = sqlite3.connect(dbfile)
        curs = conn.cursor()
        with open(csvfile, newline='', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter='|')
            for row in reader:
                insert_db = '''
                INSERT INTO %s (
                    family,
                    family_zh,
                    zh_name,
                    name,
                    fullname,
                    plant_type,
                    endemic,
                    iucn_category,
                    source)
                VALUES ("%s", "%s", "%s", "%s", "%s", %s,  %s, "%s", "%s");
                ''' % (table_name, row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8])
                curs.execute(insert_db)
                i=i+1
            conn.commit()
        conn.close()

    def dbGetsp(self, table_name, dbfile):
        conn = sqlite3.connect(dbfile)
        curs = conn.cursor()
        get_splist_sql = '''SELECT * FROM %s ORDER BY family,name;''' % table_name
        curs.execute(get_splist_sql)
        get_splist_result = curs.fetchall()
        conn.commit()
        return(get_splist_result)
        conn.close()

    def genEngine(self, dbfile, dbtable, inputfile, oformat='docx', ofile_prefix='output'):
        """
        dbfile
        ------
        sqlite database file

        dbtable
        -------

        inputfile
        ---------
        oformat 
        ofile_prefix
        """
        # check for input parameters
        #if os.path(dbfile) is True:
        #    pass
        #else:
        #    print(dbfile + " does not exist!")
        #    exit
        # check for dbtable
        conn = sqlite3.connect(dbfile)
        curs = conn.cursor()
        list_tables_sql = '''SELECT name FROM sqlite_master
            WHERE type='table' and name='%s'
            ORDER BY name;''' % dbtable
        curs.execute(list_tables_sql)
        list_tables = curs.fetchall()
        if list_tables == '':
            exit
        # vascular plants
        elif list_tables[0][0] == 'dao_pnamelist' or list_tables[0][0] == 'dao_pnamelist_apg3':
            species_type = 1
        # birds
        elif list_tables[0][0] == 'dao_bnamelist':
            species_type = 2
        else:
            species_type = 1

        #### INPUT FILES
        sample_create = '''
        CREATE TABLE sample (
          zh_name varchar
        );
        '''
        curs.execute(sample_create)
        with open(inputfile, newline='', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter='|')
            for row in reader:
                # substitute 台 to 臺
                zhname = re.sub('台([灣|北|中|西|南|東])',r'臺\1', row[0])
                insert_db = '''
                INSERT INTO sample (zh_name) VALUES ("%s");
                ''' % zhname
                curs.execute(insert_db)
                conn.commit()
        f.close()
               
        with codecs.open(ofile_prefix +'.md', 'w+', 'utf-8') as f:
            #### Generate HEADER
            if species_type == 1:
                f.write(u'# 維管束植物名錄')
                sp_note = u'"#" 代表特有種，"*" 代表歸化種，"†" 代表栽培種。'
                sp_conserv = u'''中名後面括號內的縮寫代表依照「臺灣維管束植物紅皮書初評名錄」中依照 IUCN 瀕危物種所評估等級， \
EX: 滅絕、EW: 野外滅絕、RE: 區域性滅絕、CR: 嚴重瀕臨滅絕、 \
EN: 瀕臨滅絕、VU: 易受害、NT: 接近威脅、DD: 資料不足。若未註記者代表安全(Least concern)'''
            elif species_type == 2:
                f.write(u'# 鳥類名錄')
                sp_note = u'"#" 代表特有種，"##" 代表特有亞種'
                sp_conserv = u'''中名後面括號內代表行政院農業委員會依照野生動物保護法所公布之保育等級。 \
I：表示瀕臨絕種野生動物、II：表示珍貴稀有野生動物、III：表示其他應予保育之野生動物'''
            else:
                f.write(u'# 物種名錄')
            f.write('\n')
            count_family = '''
            SELECT count(*) from (SELECT distinct family from sample s left outer join %s n 
                    on s.zh_name=n.zh_name) as f;
            ''' % dbtable
            count_species = '''
            SELECT count(*) from (SELECT distinct n.zh_name from sample s left outer join %s n 
                    on s.zh_name=n.zh_name) as f;
            ''' % dbtable
            not_exist_sp = '''
            SELECT distinct s.zh_name from sample s left outer join %s n 
                    on s.zh_name=n.zh_name where n.zh_name is null;
            ''' % dbtable
            curs.execute(count_family)
            family_no = curs.fetchall()[0][0]
            curs.execute(count_species)
            species_no = curs.fetchall()[0][0]
            curs.execute(not_exist_sp)
            no_sp = curs.fetchall()
            nsp = []
            for i in no_sp:
                nsp.append(i[0])
            nsp = ', '.join(nsp)
            if len(nsp) > 0:
                f.write('\n')
                f.write(u'<font color="red">輸入名錄中，下列物種不存在於物種資料庫中：{} ，請再次確認物種中名是否和資料庫中相同</font>\n'.format(nsp))
            f.write('\n')
            f.write(u'本名錄中共有 {} 科、{} 種，科名後括弧內為該科之物種總數。'.format(family_no, species_no))
            f.write(sp_note)
            f.write(sp_conserv)
            f.write('\n')
            ####### End of HEADER

            ####### namelist BODY
            if species_type == 1:
                pt_plant_type_sql = '''
                    SELECT p.plant_type,p.pt_name
                    FROM dao_plant_type p,
                        (SELECT distinct plant_type from sample s left outer join %s n 
                        on s.zh_name=n.zh_name order by plant_type) as t
                    WHERE p.plant_type = t.plant_type;
                ''' % dbtable
                curs.execute(pt_plant_type_sql)
                pt_plant_type = curs.fetchall()
                n = 1
                m = 1
                for i in range(0,len(pt_plant_type)):
                    f.write('\n')
                    f.write('\n###'+pt_plant_type[i][1]+'\n\n')
                    taxa_family_sql = '''
                    select distinct family,family_zh from sample s left outer join %s n 
                    on s.zh_name=n.zh_name where n.plant_type=%i
                    order by plant_type,family;
                    ''' % (dbtable, pt_plant_type[i][0])
                    curs.execute(taxa_family_sql)
                    taxa_family = curs.fetchall()
                    for j in range(0,len(taxa_family)):
                        sp_number_in_fam = '''
                        select count(*) from 
                            (select distinct fullname,n.zh_name from sample s left outer join %s n 
                            on s.zh_name=n.zh_name where n.plant_type=%i and family='%s'
                            order by plant_type,family,fullname) as a;
                        ''' % (dbtable, pt_plant_type[i][0], taxa_family[j][0])
                        curs.execute(sp_number_in_fam)
                        fam_spno = curs.fetchall()[0][0]
                        fam = str(m) + '. **' + taxa_family[j][0]
                        fam_zh = taxa_family[j][1]+'**'
                        f.write('\n')
                        f.write(fam+' '+fam_zh+' (%i)\n' % fam_spno)
                        taxa_family_sp = '''
                            select distinct fullname,n.zh_name,n.endemic,n.source,n.iucn_category from sample s left outer join %s n 
                            on s.zh_name=n.zh_name where n.plant_type=%i and family='%s'
                            order by plant_type,family,fullname;
                        ''' % (dbtable, pt_plant_type[i][0], taxa_family[j][0])
                        curs.execute(taxa_family_sp)
                        taxa_family_sp = curs.fetchall()
                        m = m + 1
                        # output species within a family
                        for k in range(0,len(taxa_family_sp)):
                            # check the endmic species
                            if taxa_family_sp[k][2] == 1:
                                ENDEMIC = "#"
                            else:
                                ENDEMIC = ''
                            # check the source 
                            if taxa_family_sp[k][3] == u'栽培':
                                SRC = '†'
                            elif taxa_family_sp[k][3] == u'歸化':
                                SRC = '*'
                            else:
                                SRC = ''
                            # IUCN category
                            if len(taxa_family_sp[k][4]) == 2:
                                IUCNCAT = ' (%s)' % taxa_family_sp[k][4]
                            else:
                                IUCNCAT = ''
                            spinfo = ' ' + ENDEMIC + SRC + IUCNCAT
                            if spinfo is not None:
                                f.write('    ' + str(n) + '. ' + self.fmtname(taxa_family_sp[k][0]) + ' ' + taxa_family_sp[k][1] + spinfo + '\n')
                            else:
                                f.write('    ' + str(n) + '. ' + self.fmtname(taxa_family_sp[k][0]) + ' ' + taxa_family_sp[k][1] +'\n')
                            n = n + 1
            else:
                taxa_family_sql = '''
                    SELECT DISTINCT 
                        family,family_zh 
                    FROM sample s 
                    LEFT OUTER JOIN %s n 
                    ON s.zh_name=n.zh_name
                    ORDER BY family;
                    ''' % dbtable
                curs.execute(taxa_family_sql)
                taxa_family = curs.fetchall()

                m = 1
                n = 1
                for j in range(0,len(taxa_family)):
                    sp_number_in_fam = '''
                        select count(*) from 
                        (SELECT distinct name,n.zh_name
                            FROM sample s LEFT OUTER JOIN %s n 
                            ON s.zh_name=n.zh_name 
                        WHERE family='%s'
                        ORDER BY family,name) as a;
                    ''' % (dbtable, taxa_family[j][0])
                    curs.execute(sp_number_in_fam)
                    fam_spno = curs.fetchall()[0][0]
                    fam = str(m) + '. **' + taxa_family[j][0]
                    fam_zh = taxa_family[j][1]+'**'
                    f.write('\n')
                    f.write(fam+' '+fam_zh+' (%i)\n' % fam_spno)
                    taxa_family_sp = '''
                        SELECT distinct 
                            name,n.zh_name,n.endemic,n.consv_status 
                        FROM sample s LEFT OUTER JOIN %s n 
                            ON s.zh_name=n.zh_name 
                        WHERE 
                            family='%s'
                        ORDER BY family,name;
                    ''' % (dbtable, taxa_family[j][0])
                    curs.execute(taxa_family_sp)
                    taxa_family_sp = curs.fetchall()
                    m = m + 1
                    # output species within a family
                    for k in range(0,len(taxa_family_sp)):
                        # check the endmic species
                        if taxa_family_sp[k][2] == u'特有種':
                            ENDEMIC = "#"
                        elif taxa_family_sp[k][2][0:4] == u'特有亞種':
                            ENDEMIC = '##'
                        else:
                            ENDEMIC = ''
                        # conservation status 
                        CONSERV = taxa_family_sp[k][3]
                        spinfo = ' ' + ENDEMIC + CONSERV
                        if spinfo is not None:
                            f.write('    ' + str(n) + '. ' + self.fmtname(taxa_family_sp[k][0]) + ' ' + taxa_family_sp[k][1] + spinfo + '\n')
                        else:
                            f.write('    ' + str(n) + '. ' + self.fmtname(taxa_family_sp[k][0]) + ' ' + taxa_family_sp[k][1] +'\n')
                        n = n + 1
            f.close()        
            try:
            #    pypandoc.convert(ofile_prefix + '.md', oformat, outputfile=ofile_prefix+'.'+oformat)
                self.pandocConvert(oformat, ofile_prefix)
            except BaseException as e:
                print(str(e))
            curs.execute('DROP TABLE IF EXISTS sample;')
            conn.commit()
            conn.close()