import re,regex


class attrValue_RegexGenerator:

    def __init__(self, literal_chars):
        self.literal_chras = literal_chars
    
        self.split_characters = ["\n","(<br>)","、","・",","," ","×","/","，",'\\s','x',]
    def _get_unit_from_mastersheet(self):
        spreadsheet_url ='' 
        units = gc.open_by_url(spreadsheet_url)
        st = units.worksheet("シート1")
        unit_dicts = st.get_all_records()
        unit = [ u['unit'] for u in unit_dicts]
        return unit

    def _get_jp_literal_from_mastersheet(self):
        spreadsheet_url = "" 
        num_split = gc.open_by_url(spreadsheet_url)
        st = num_split.worksheet("シート1")
        dic = st.get_all_records()
        attrValue_patterns = pl.from_records(dic)
        jp_literals = [regex.findall('[\p{Script=Han}\p{Script=Katakana}\p{Script=Hiragana}]{1,}', ap[0] ) for ap in attrValue_patterns.get_column('attrValue')]
        return jp_literals


    def _define_literal_chars(self):
        units = sorted(self._get_unit_from_mastersheet(),key=len,reverse =True)
        #なんらかの文字の後ろにunitがある仮定
        units_re ="(?:\s|\d|>|\)|\()(" + "|".join(units) +")\)?"
        units_re = units_re.replace("-","\-").replace("[","\[").replace("]","\]")
        
        '''
        priority = ["約","以下","以内","未満","以上","まで"
                    ,"推奨","最高","最小","最大","最低","参考","外径",
                    "内径","長さ","高さ","幅","奥行","間口","サイズ",
                    "max","MAX","min","MIN","<sup>\-?\d+</sup>",
                    "<br>","外寸","内寸","有効内寸","W×D×H","耐荷重",
                    "重量","内容量","容量","車輪径","全高","取付高"] 
        '''
        jp_literals = self._get_jp_literal_from_mastersheet()
        jp_literals_re ="(" + "|".join(jp_literals) +")"

        # 数値の前にある文字
        kigo = ['W', 'M',"L","H","D","P",'S',"VP","各","X","x"]
        kigo_re ="(?:\d|\s|\(|×)?(" + "|".join(prefix) +")(?:\d|\s|：|:|\)|×)"

        #　グループで限定する文字
        pttn_list  =[ ['PT', 'Pt', 'RC', 'Rc', 'RP', 'Rp', 'PS', 'Ps', 'G', 'PF', 'Pf', 'PJ', "R"],
                    ["KF","NW"],
                    ["メネジ","めねじ","オネジ","おねじ","雄","雌","オス","メス"],
                    ["NPTF","NPT","NPSF"],
                    ["単相","三相","3相"],
                    ["AC","DC"],
                    ["UNF","UNC"],
                    
        ]
        multi_re_list = sorted(["(" + "|".join(l) +")" for l in pttn_list],key=len)

        re_list = [units_re,jp_literals_re,kigo_re,multi_re_list]

    def _get_literal_chars(self):
        return self.literal_chras 

    def _word2symbol(self,attrValue:str):
        word = attrValue
        word = re.escape(word)
        p = regex.compile(r'[\p{Script=Hiragana}\p{Script=Katakana}\p{Script=Han}A-Za-zー]+')
        word = p.sub("[文字]",word)
        p = regex.compile(r'\d*?[ ・-]?(1/2|3/8|3/4|1/4|1/8)[""]?')
        word = p.sub("[呼び径]",word)
        p = regex.compile(r'\d+(,\.\d+)?')
        word = p.sub("[数値]",word)
        word = word.replace('\\ ','\\s')
        return word

    def _literal_word2symbol(self, attrValue: str, literal_word_regex_list: list , is_save_regex_phase :bool):
        lit_word2idx = []

        for literal_word_regex in literal_word_regex_list:

            pattern = re.compile(literal_word_regex)
            for match in re.finditer(pattern, attrValue):

                e = match.groups()[0]
                idx = match.start()
                elm = literal_word_regex if is_save_regex_phase else e
                lit_word2idx.append((elm, idx))
                attrValue = attrValue[:idx] + '!' * len(elm) + attrValue[idx+len(e):]

        return attrValue, lit_word2idx


    def _symbol2literal_word(self,attrValue:str, mappings : list):
        mappings = sorted(mappings,key = lambda x : x[1])
        for i in range(len(mappings)):
            attrValue = re.sub('!{1,}',mappings[i][0],attrValue,1)
        return attrValue

    def _convert_to_symbol(self,attrValue):

        literal_word_regex_list = self._get_literal_chars()
        word2symbol_list = []
        symbolized_attrValue = attrValue

        #正規表現に変換しない文字（リテラル）をシンボルに変換
        for i in range(len(literal_word_regex_list)):
            is_save_regex_phase = True if i == len(literal_word_regex_list)-1 else False
            symbolized_attrValue,map_word2symbol = self._literal_word2symbol(symbolized_attrValue,literal_word_regex_list[i],is_save_regex_phase)
            word2symbol_list.extend(map_word2symbol) 
        #正規表現に変換する文字をシンボルに変換 
        symbolized_attrValue = self._word2symbol(symbolized_attrValue)
        #リテラルのシンボルは元の文字に戻す
        symbolized_attrValue = self._symbol2literal_word(symbolized_attrValue,word2symbol_list)
        return symbolized_attrValue



    def _symbol2regex(self,symbolized_attrValue):
        to_regex = lambda s : s.replace("[呼び径]",'\d*?[ ・-]?(1/2|3/8|3/4|1/4|1/8)?[""]?').replace("[文字]","[\p{Han}\p{Katakana}\p{Hiragana}A-Za-zー]+").replace("[管種類]","(R|PT|Pt|RC|Rc|RP|Rp|PS|Ps|G|PF|Pf|PJ)").replace("[数値]","[\d,]+(\.\d+)?")
        return "^"+to_regex(symbolized_attrValue)+"$"

    def _sequential_symbol2regex(self,symbolized_attrValue,split_str): 
        to_regex = lambda s : s.replace("[呼び径]",'\d*?[ ・-]?(1/2|3/8|3/4|1/4|1/8)?[""]?').replace("[文字]","[\p{Han}\p{Katakana}\p{Hiragana}A-Za-zー]+").replace("[管種類]","(R|PT|Pt|RC|Rc|RP|Rp|PS|Ps|G|PF|Pf|PJ)").replace("[数値]","[\d,]+(\.\d+)?")
        return f"^({split_str}?" + to_regex(symbolized_attrValue) + "){1,}$"
    
    def _is_sequential(self,symbolized_attrValue):
        result = (False,None,None)
        for split_char in self.split_characters:
            splited_av =symbolized_attrValue.split(split_char)
            if len(splited_av)!=1 and len(set(splited_av)) == 1:
                result = (True,split_char,splited_av[0])
                return result
        return result
    def _attrValue2regex(self,attrValue):
        gen_regex = ''
        symbolized_attrValue = self._convert_to_symbol(attrValue)
        is_sequential,split_char,symbolized_attrValue_element = self._is_sequential(symbolized_attrValue)
        if is_sequential:
            gen_regex = self._sequential_symbol2regex(symbolized_attrValue_element,split_char)
        else:
            gen_regex = self._symbol2regex(symbolized_attrValue) 

        gen_regex = r"\n".join(gen_regex.split("\n"))
        return gen_regex


import pytest

def test1():
    s='RC1/2"×幅100mm, 最大100m, 最小10m'
    lc = [['(kfg|mm|m)'], ['(最大|最小)(?:\d|\s)'],['(幅)'],['(RC|Rc|R)','(単相|三相|3相)'] ]
    avpg = attrValue_RegexGenerator(lc)
    result = avpg._attrValue2regex(s)

    print(result)
    assert s == re.search(result,s).group()

def test2():
    s = '(ねじ込み)100m,(叩き込み)10m'
    lc = [['(kfg|mm|m)'], ['(最大|最小)(?:\d|\s)'],['(幅)'],['(RC|Rc|R)','(単相|三相|3相)'] ]
    avpg = attrValue_RegexGenerator(lc)
    result = avpg._attrValue2regex(s)
    print(result)
    assert s == re.search(result,s).group()


