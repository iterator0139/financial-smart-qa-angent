plan_react_prompt = """
Example:
请帮我计算，在20210105，中信行业分类划分的一级行业为综合金融行业中，涨跌幅最大股票的股票代码是？涨跌幅是多少？百分数保留两位小数。股票涨跌幅定义为：（收盘价 - 前一日收盘价 / 前一日收盘价）* 100%。

Thought 1 我需要查看已有信息，结合任务描述，判断这是一个文档信息查询任务，还是数据库信息查询任务。
Action 1 CheckDBInfo
Observation 1 
数据库基本信息
基金基本信息 表结构:
基金代码 (TEXT) 
基金全称 (TEXT) 
基金简称 (TEXT) 
管理人 (TEXT) 
托管人 (TEXT) 
基金类型 (TEXT) 
成立日期 (TEXT) 
到期日期 (TEXT) 
管理费率 (TEXT) 
托管费率 (TEXT) 

基金股票持仓明细 表结构:
基金代码 (TEXT) 
基金简称 (TEXT) 
持仓日期 (TEXT) 
股票代码 (TEXT) 
股票名称 (TEXT) 
数量 (REAL) 
市值 (REAL) 
市值占基金资产净值比 (REAL) 
第N大重仓股 (INTEGER) 
所在证券市场 (TEXT) 
所属国家(地区) (TEXT) 
报告类型 (TEXT) 

基金债券持仓明细
表结构:
基金代码 (TEXT) 
基金简称 (TEXT) 
持仓日期 (TEXT) 
债券类型 (TEXT) 
债券名称 (TEXT) 
持债数量 (REAL) 
持债市值 (REAL) 
持债市值占基金资产净值比 (REAL) 
第N大重仓股 (INTEGER) 
所在证券市场 (TEXT) 
所属国家(地区) (TEXT) 
报告类型 (TEXT) 

基金可转债持仓明细 表结构:
基金代码 (TEXT) 
基金简称 (TEXT) 
持仓日期 (TEXT) 
对应股票代码 (TEXT) 
债券名称 (TEXT) 
数量 (REAL) 
市值 (REAL) 
市值占基金资产净值比 (REAL) 
第N大重仓股 (INTEGER) 
所在证券市场 (TEXT) 
所属国家(地区) (TEXT) 
报告类型 (TEXT) 

基金日行情表 表结构:
基金代码 (TEXT) 
交易日期 (TEXT) 
单位净值 (REAL) 
复权单位净值 (REAL) 
累计单位净值 (REAL) 
资产净值 (REAL) 

A股票日行情表 表结构:
股票代码 (TEXT) 
交易日 (TEXT) 
昨收盘(元) (REAL) 
今开盘(元) (REAL) 
最高价(元) (REAL) 
最低价(元) (REAL) 
收盘价(元) (REAL) 
成交量(股) (REAL) 
成交金额(元) (REAL) 

港股票日行情表 表结构:
股票代码 (TEXT) 
交易日 (TEXT) 
昨收盘(元) (REAL) 
今开盘(元) (REAL) 
最高价(元) (REAL) 
最低价(元) (REAL) 
收盘价(元) (REAL) 
成交量(股) (REAL) 
成交金额(元) (REAL) 

A股公司行业划分表 表结构:
股票代码 (TEXT) 
交易日期 (TEXT) 
行业划分标准 (TEXT) 
一级行业名称 (TEXT) 
二级行业名称 (TEXT) 

基金规模变动表 表结构:
基金代码 (TEXT) 
基金简称 (TEXT) 
公告日期 (TIMESTAMP) 
截止日期 (TIMESTAMP) 
报告期期初基金总份额 (REAL) 
报告期基金总申购份额 (REAL) 
报告期基金总赎回份额 (REAL) 
报告期期末基金总份额 (REAL) 
定期报告所属年度 (INTEGER) 
报告类型 (TEXT) 

基金份额持有人结构 表结构:
基金代码 (TEXT) 
基金简称 (TEXT) 
公告日期 (TIMESTAMP) 
截止日期 (TIMESTAMP) 
机构投资者持有的基金份额 (REAL) 
机构投资者持有的基金份额占总份额比例 (REAL) 
个人投资者持有的基金份额 (REAL) 
个人投资者持有的基金份额占总份额比例 (REAL) 
定期报告所属年度 (INTEGER) 
报告类型 (TEXT) 


Thought 2 
任务要求查询在20210105，中信行业分类划分的一级行业为综合金融行业中，涨跌幅最大股票的股票代码和涨跌幅。
DB中有A股票日行情表和港股股票日行情表，可以查询到股票代码和涨跌幅。所以这是一个数据库信息查询任务。
下一步我需要根据已有的DB表数据，将任务要求转换为SQL查询语句，并执行查询。

Action 2 [QueryToSQL]
Observation 2 
SELECT "股票代码" ,   ROUND((("收盘价(元)" - "昨收盘(元)") / "昨收盘(元)" * 100),2) AS "涨跌幅" 
FROM "A股票日行情表" 
WHERE "股票代码" IN (SELECT DISTINCT "股票代码"  from "A股公司行业划分表" WHERE 行业划分标准= "中信行业分类" AND 一级行业名称="综合金融") 
AND  "交易日" = "20210105"
ORDER BY "涨跌幅" DESC
LIMIT 1;

Thought 3 我需要执行SQL查询语句，获取涨跌幅最大股票的股票代码和涨跌幅。
Action 3 [QueryDB]
Observation 3 
{
    "股票代码": "600120",
    "涨跌幅": 0.0
}

Thought 4 在20210105，中信行业分类划分的一级行业为综合金融行业中，涨跌幅最大股票的股票代码是600120，涨跌幅是0.00%。
Action 4 Finish[SUPPORTS]

"""