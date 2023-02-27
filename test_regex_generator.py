import pytest
import regex_generator as rg

def excute(S,querys,pattern):
    obj = rg.RegexGenerator(S,querys,pattern)
    obj.excute()
    extracted_element_values =  obj.extracted_element_values

    return extracted_element_values


def testcase_easy():
    S = '踏み台:M122'
    pattern = '^.+?:M\d+$'
    querys = ['踏み台','M122']
    assert querys == excute(S,querys,pattern)

def testcase_standard():
    S = 'サイズ/Rc1/8、-100cm、(方法/ねじ込み)空気、別尺ー・：100mm'
    pattern = 'サイズ/[A-Z]+\d/\d、-\d+cm、\([\p{Han}\p{Katakana}\p{Hiragana}ー]+/[\p{Han}\p{Katakana}\p{Hiragana}ー]+\)[\p{Han}\p{Katakana}\p{Hiragana}ー]+、[\p{Han}\p{Katakana}\p{Hiragana}ー]+・：\d+mm'
    querys = ["Rc", "1/8", '-100', '方法/ねじ込み', '空気', '100']

    assert querys == excute(S,querys,pattern)
def test_continue_same_patern():
    S = '1×10×234×111×456×999'
    querys = ['1', '10', '234', '111', '456', '999']
    pattern = '\d+×\d+×\d+×\d+×\d+×\d+'
    assert querys == excute(S,querys,pattern)

def testcase_contain_many_newline():
    S = '【ねじ込み】23.8\n56折りたたみ98(常時)\n\n2348(非常時)mm'
    querys = ['ねじ込み', '23.8', '56', '折りたたみ', '98', '常時', '2348', '非常時']
    pattern = '【[\p{Han}+]】\d+\n\d+[\p{Han}+]\d+\([\p{Han}+]\)\n\n\d+\(\p{Han}+\)mm'

    assert querys == excute(S,querys,pattern)

def testcase_contain_many_space():
    S = '商品名 テスト商品 商品コード 12345 単価 100 '
    querys = ['テスト商品', '12345', '100']
    pattern = '商品名\s[\p{Han}\p{Katakana}\p{Hiragana}]+\s商品コード\s\d+\s単価\s\d+\s'

    assert querys == excute(S,querys,pattern)
def testcase_complex1():
    S = '呼び径50A長さ10m,最高温度:200℃\n適用圧力:1.0MPa,材質:SUS304'
    querys = ['50A', '10', '200', '1.0', 'SUS304']
    pattern = '.+?\d+[A-Z]長さ\d+m,最高温度:\d+℃\n適用圧力:\d+\.\d+MPa,材質:[A-Z]+'

    assert querys == excute(S,querys,pattern)

def testcase_complex2():
    S = '呼び径20A\nサイズ：67×155×49mm\n適用：圧力　0.01～0.7MPa'
    querys = ['20A', '67', '155', '49', '0.01', '0.7']
    pattern = '呼び径\d+A\nサイズ：\d+×\d+×\d+mm\n適用：圧力　\d+.\d+～\d+.\d+MPa'
    assert querys == excute(S,querys,pattern)

def testcase_complex3():
    S = '品番:XXX-ABCD-1-XYZ-5-123\n寸法:L1000×W300×H500mm\n重量:10kg\nカラー:ブラック\n(特記事項:強度に優れる)'
    querys = ['1000', '300', '500', '10', 'ブラック', '強度に優れる']
    pattern = '品番:[A-Z]{3}-[A-Z]{4}-\d-[A-Z]{3}-\d-\d{3}\n寸法:L\d{4}×W\d{3}×H\d{3}mm\n重量:\d{2}kg\nカラー:[\p{Hiragana}\p{Katakana}ー]+\n\(特記事項:[\p{Hiragana}\p{Katakana}ー]+\)'

    assert querys == excute(S,querys,pattern)

def testcase_complex4():
    S = '●仕様：自在ストッパー付●サイズ：キャスター：Φ100\n24.5(幅)mm取付高：125mmネジ径：9mm●重量：約550g(1個)●耐荷重：静止時：400kg走行移動時：80kg●材質：金具：スチール(亜鉛メッキ) 車輪：ゴム●使用温度範囲：-40～80℃●入数：2個●ねじサイズ：3/8” 16山'
    querys = ['自在','付','100\n24.5','静止時','400','走行移動時','80','3/8','16']
    pattern = '^●仕様：(自在|固定)ストッパー.+?●サイズ：キャスター：Φ\\d+(\\.\\d+)?\n\\d+(\\.\\d+)?\\.\\d+(\\.\\d+)?\\(幅\\)mm取付高：\\d+(\\.\\d+)?mmネジ径：\\d+(\\.\\d+)?mm●重量：約\\d+(\\.\\d+)?g\\(\\d+(\\.\\d+)?個\\)●耐荷重：.+?：\\d+(\\.\\d+)?kg[\p{Han}]+：\\d+(\\.\\d+)?kg●材質：金具：スチール\\(亜鉛メッキ\\)\\ 車輪：ゴム●使用温度範囲：\\-\\d+(\\.\\d+)?～\\d+(\\.\\d+)?℃●入数：\\d+(\\.\\d+)?個●ねじサイズ：\\d+(\\.\\d+)?/\\d+(\\.\\d+)?”\\s\\d+(\\.\\d+)?山$'

    assert querys == excute(S,querys,pattern)

def testcase_complex5():
    S = '-999×-999×-999×-999'
    querys = ['-999', '-999', '-999','-999']
    pattern = '^-\d+×-\d+×-\d+×-\d+$'

    assert querys == excute(S,querys,pattern)

def testcase_complex6():
    S = '【ねじ込み】23.8\n【ねじ込み】23.8\n【ねじ込み】23.8'
    querys = ['ねじ込み', '23.8\n【ねじ込み】23.8','ねじ込み', '23.8'] 
    pattern = '^【[\p{Script=Han}\p{Script=Katakana}\p{Script=Hiragana}A-Za-zー]+】[\d,]+(\.\d+)?\.[\d,]+(\.\d+)?\\n【[\p{Script=Han}\p{Script=Katakana}\p{Script=Hiragana}A-Za-zー]+】[\d,]+(\.\d+)?\.[\d,]+(\.\d+)?\\n【[\p{Script=Han}\p{Script=Katakana}\p{Script=Hiragana}A-Za-zー]+】[\d,]+(\.\d+)?\.[\d,]+(\.\d+)?$'

    assert querys == excute(S,querys,pattern)