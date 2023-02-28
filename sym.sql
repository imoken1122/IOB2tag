CREATE  TEMPORARY FUNCTION NGRAM(str STRING, n INT64)
RETURNS ARRAY<STRING> AS ((
  SELECT ARRAY(SELECT SUBSTR(str, seq, n) FROM UNNEST(T.seqs) AS seq)
   FROM (
    SELECT str, GENERATE_ARRAY(1, LENGTH(str) - n + 1) AS seqs
  ) AS T
));

CREATE TEMPORARY FUNCTION BIGRAM(str STRING)
RETURNS ARRAY<STRING> AS (NGRAM(str, 2));

CREATE TEMPORARY FUNCTION TRIGRAM(str STRING)
RETURNS ARRAY<STRING> AS (NGRAM(str, 3));

CREATE TEMPORARY FUNCTION LEVENSHTEIN_SIM(str1 STRING, str2 STRING)
RETURNS FLOAT64
LANGUAGE js AS """
  var str1Len = str1.length;
  var str2Len = str2.length;
  
  if (str1Len === 0) {
    return str2Len;
  }
  
  if (str2Len === 0) {
    return str1Len;
  }
  
  var matrix = [];
  
  for (var i = 0; i <= str1Len; i++) {
    matrix[i] = [i];
  }
  
  for (var j = 0; j <= str2Len; j++) {
    matrix[0][j] = j;
  }
  
  for (var i = 1; i <= str1Len; i++) {
    for (var j = 1; j <= str2Len; j++) {
      if (str1.charAt(i-1) == str2.charAt(j-1)) {
        matrix[i][j] = matrix[i-1][j-1];
      } else {
        matrix[i][j] = Math.min(
          matrix[i-1][j-1] + 1,  // substitution
          matrix[i][j-1] + 1,    // insertion
          matrix[i-1][j] + 1     // deletion
        );
      }
    }
  }
  
  var distance = matrix[str1Len][str2Len];
  return 1 - (distance / Math.max(str1Len, str2Len));
""";


CREATE TEMPORARY FUNCTION jaccard_similarity(a ARRAY<STRING>, b ARRAY<STRING>)
RETURNS FLOAT64
LANGUAGE js AS """
  const s1 = new Set(a);
  const s2 = new Set(b);

  const intersection = new Set([...s1].filter(x => s2.has(x)));
  const union = new Set([...s1, ...s2]);

  return union.size === 0 ? 0 : intersection.size / union.size;
""";


WITH table1 AS (
  SELECT '111' as code,'奥行き' AS name, '123' AS value UNION ALL
  SELECT '123','車輪径', 'φ36' UNION ALL
  SELECT '909','キャスター', '固定' UNION ALL
  SELECT '456','使用キャスター', '固定４輪、89φ' UNION ALL
  SELECT '456','使用キャスター', '自在２輪' UNION ALL
    SELECT '456','使用キャスター', '自在２輪' UNION ALL
  SELECT '12993','キャスター径', 'φ90' UNION ALL
  SELECT '909','キャスター', 'φ23(自在)' UNION ALL
  SELECT '333','仕様', '材料；ステンレス、車輪；自在２輪φ23(自在)、サイズ；100'

),
group_category as (
  select distinct code,name,value, regexp_replace(regexp_replace(regexp_replace(value, r'[\p{Han}\p{Katakana}\p{Hiragana}A-Za-z]+', '[文字]'), r'\d*?[ ・-]?(1/2|3/8|3/4|1/4|1/8)[""]?','[呼び径]'),r'([\d,]+(\.\d+)?|[０-９]+)', '[数字]') as regex_value
  from table1
  group by code,value,name

),
cross_join_table as(
  select a.code as codea, a.name as namea,a.value as valuea,b.code as codeb, b.name as nameb, b.value as valueb, a.regex_value as regexa, b.regex_value as regexb
  from group_category as a
  cross join group_category as b
  where a.code != b.code
),
similarity as (
  select distinct codea,codeb,namea,nameb ,valuea, valueb,(fhoffa.x.median(ARRAY_AGG(LEVENSHTEIN_SIM(valuea, valueb)))*0.5 + fhoffa.x.median(ARRAY_AGG(LEVENSHTEIN_SIM(regexa,regexb)))*0.5) as score1,fhoffa.x.median(ARRAY_AGG(LEVENSHTEIN_SIM(namea,nameb))) as score2
  from cross_join_table
  group by codea,codeb,namea, nameb,valuea,valueb

)


select namea,nameb,avg(score1) as score1,avg(score2) as score2
from similarity
where codea = '456'
group by namea,nameb
order by score1 desc

