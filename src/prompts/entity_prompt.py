entity_definition = [
    {
      "category": "基金类",
      "entities": [
        { "name": "基金", "unique": True, "example": "易方达蓝筹精选混合", "description": "公募或私募基金的具体名称" },
        { "name": "基金代码", "unique": True, "example": "005827", "description": "唯一标识基金的六位代码" },
        { "name": "基金简称", "unique": False, "example": "易方达蓝筹", "description": "基金的简称或通用名称" },
        { "name": "基金管理人", "unique": True, "example": "易方达基金管理有限公司", "description": "管理基金资产的机构" },
        { "name": "基金托管人", "unique": True, "example": "工商银行", "description": "托管基金资产的金融机构" },
        { "name": "基金类型", "unique": False, "example": "混合型", "description": "基金的投资策略类型" },
        { "name": "基金报告类型", "unique": False, "example": "年报", "description": "基金披露的报告种类" }
      ]
    },
    {
      "category": "股票类",
      "entities": [
        { "name": "股票", "unique": True, "example": "贵州茅台", "description": "股票名称" },
        { "name": "股票代码", "unique": True, "example": "600519", "description": "A股或港股的股票代码" },
        { "name": "证券市场", "unique": False, "example": "A股", "description": "股票交易市场" },
        { "name": "所属国家或地区", "unique": False, "example": "中国大陆", "description": "股票发行公司所在地" }
      ]
    },
    {
      "category": "债券类",
      "entities": [
        { "name": "债券", "unique": True, "example": "22国债03", "description": "基金持有的债券名称" },
        { "name": "债券类型", "unique": False, "example": "国债", "description": "债券分类" },
        { "name": "可转债", "unique": True, "example": "宁德转债", "description": "可转换为股票的债券" }
      ]
    },
    {
      "category": "行业类",
      "entities": [
        { "name": "行业", "unique": True, "example": "金融", "description": "股票或公司所属行业" },
        { "name": "行业划分标准", "unique": False, "example": "申万", "description": "行业分类依据标准" }
      ]
    },
    {
      "category": "时间类",
      "entities": [
        { "name": "持仓日期", "unique": True, "example": "2023-03-31", "description": "基金持仓数据的披露时间点" },
        { "name": "交易日期", "unique": True, "example": "2023-04-01", "description": "股票行情时间点" },
        { "name": "公告日期", "unique": True, "example": "2023-06-30", "description": "报告文件或事件披露时间" },
        { "name": "报告期截止日期", "unique": True, "example": "2023-12-31", "description": "报告覆盖的截止时间" },
        { "name": "成立日期", "unique": True, "example": "2018-05-01", "description": "基金成立时间" },
        { "name": "到期日期", "unique": True, "example": "2028-05-01", "description": "基金或债券的到期时间" },
        { "name": "报告所属年度", "unique": True, "example": "2023", "description": "报告所属年份" }
      ]
    },
    {
      "category": "行情指标类",
      "entities": [
        { "name": "单位净值", "unique": False, "example": "1.2370", "description": "基金每日每单位价值" },
        { "name": "累计单位净值", "unique": False, "example": "3.4912", "description": "基金自成立以来总净值" },
        { "name": "成交量", "unique": False, "example": "1000万股", "description": "股票日交易数量" },
        { "name": "成交金额", "unique": False, "example": "12亿元", "description": "股票日交易金额" },
        { "name": "收盘价", "unique": False, "example": "128.34元", "description": "收盘价" },
        { "name": "开盘价", "unique": False, "example": "126.50元", "description": "开盘价" },
        { "name": "最高价", "unique": False, "example": "130.00元", "description": "当日最高价" },
        { "name": "最低价", "unique": False, "example": "125.80元", "description": "当日最低价" }
      ]
    },
    {
      "category": "机构与人员类",
      "entities": [
        { "name": "机构投资者", "unique": False, "example": "全国社保基金", "description": "基金持有人中的机构" },
        { "name": "个人投资者", "unique": False, "example": "张三", "description": "基金持有人中的自然人" },
        { "name": "承销商", "unique": True, "example": "中信证券", "description": "招股说明书中的承销机构" },
        { "name": "保荐机构", "unique": True, "example": "中金公司", "description": "招股说明书中的保荐人" },
        { "name": "自然人", "unique": True, "example": "王五", "description": "公司高管、股东、发起人等个体" }
      ]
    },
    {
      "category": "文档类",
      "entities": [
        { "name": "公司名称", "unique": True, "example": "江苏爱康太阳能科技股份有限公司", "description": "招股说明书所描述的发行主体公司" },
        { "name": "控股股东", "unique": True, "example": "爱康控股集团有限公司", "description": "控制该公司经营的重要股东" },
        { "name": "发起人股东", "unique": False, "example": "张三", "description": "公司设立初期出资人" },
        { "name": "主承销商", "unique": True, "example": "国泰君安证券", "description": "发行过程的主承销商" },
        { "name": "招股说明书编号", "unique": True, "example": "ZBG20231212-002", "description": "招股说明书文档的唯一标识" },
        { "name": "发行方式", "unique": False, "example": "网下配售", "description": "股票发行方式" }
      ]
    },
    {
      "category": "通用实体",
      "entities": [
        { "name": "金额", "unique": False, "example": "123456789元", "description": "用于表示金额（可含单位）" },
        { "name": "百分比", "unique": False, "example": "23.45%", "description": "百分比值" },
        { "name": "数量", "unique": False, "example": "1200万股", "description": "带单位的数量" },
        { "name": "日期", "unique": False, "example": "2023-03-31", "description": "标准日期" },
        { "name": "时间段", "unique": False, "example": "2023年1月到6月", "description": "一段时间区间" },
        { "name": "地址", "unique": False, "example": "北京市西城区复兴门内大街XX号", "description": "地理位置或办公地址" },
        { "name": "机构名", "unique": True, "example": "中信证券", "description": "金融、审计等专业机构名称" }
      ]
    }
]

entity_relation = [
    { "head": "基金", "tail": "股票", "type": "持仓", "description": "基金持有某股票" },
    { "head": "基金", "tail": "债券", "type": "持仓", "description": "基金持有某债券" },
    { "head": "基金", "tail": "可转债", "type": "持仓", "description": "基金持有某可转债" },
    { "head": "基金", "tail": "基金管理人", "type": "管理", "description": "基金由某机构管理" },
    { "head": "基金", "tail": "基金托管人", "type": "托管", "description": "基金由某机构托管" },
    { "head": "股票", "tail": "行业", "type": "所属", "description": "股票所属行业" },
    { "head": "可转债", "tail": "股票", "type": "转换为", "description": "可转债可转为某股票" },
    { "head": "公司名称", "tail": "控股股东", "type": "控股", "description": "公司由该股东控股" },
    { "head": "公司名称", "tail": "主承销商", "type": "承销", "description": "公司股票由主承销商承销" },
    { "head": "招股说明书", "tail": "公司名称", "type": "描述对象", "description": "招股说明书对应的公司" }
]

ENTITY_EXTRACTION_PROMPT = """
你是一个结构化信息抽取助手，请根据下方提供的实体类型定义，从输入文本中抽取出所有匹配的实体。输出格式要求为 JSON，且字段名严格一致。

【实体类型定义】
{entity_definition}

【实体关系定义】
{entity_relation}

【任务要求】
- 请识别并抽取文本中出现的所有实体，输出每个实体的：
  - `entity_type`: 实体类型名（如"基金"、"股票"、"金额"等）
  - `text`: 实体在文本中出现的原文
  - `start`: 实体在原文中的起始字符位置（从0开始计数）
  - `end`: 实体在原文中的结束字符位置（不包括该位置字符）
- 若多个实体重叠，请全部保留（不进行去重）
- 请识别并抽取文本中出现的所有实体关系，输出每个实体关系的：
  - `head`: 实体关系中的头实体
  - `tail`: 实体关系中的尾实体
  - `type`: 实体关系类型
  - `description`: 实体关系描述
- 请以 JSON 数组形式输出所有抽取到的实体和实体关系，通过两个字段来区分，分别是：
  - `entities`: 实体json数组
  - `relations`: 实体关系json数组
- 不要输出多余说明或解释，只返回 JSON 结果

【示例文本】
易方达蓝筹精选混合（基金代码：005827）在2023年第一季度持有贵州茅台（600519）1200万股，持仓市值为123亿元，位居第一大重仓股。

【示例输出】
{
  "entities": [
  { "entity_type": "基金", "text": "易方达蓝筹精选混合", "start": 0, "end": 11 },
  { "entity_type": "基金代码", "text": "005827", "start": 18, "end": 24 },
  { "entity_type": "日期", "text": "2023年第一季度", "start": 25, "end": 34 },
  { "entity_type": "股票", "text": "贵州茅台", "start": 37, "end": 41 },
  { "entity_type": "股票代码", "text": "600519", "start": 42, "end": 48 },
  { "entity_type": "数量", "text": "1200万股", "start": 49, "end": 54 },
  { "entity_type": "金额", "text": "123亿元", "start": 60, "end": 65 }
],
  "relations": [
    { "head": "基金", "tail": "股票", "type": "持仓", "description": "基金持有某股票" },
    { "head": "股票", "tail": "数量", "type": "持仓", "description": "股票持仓数量" },
    { "head": "股票", "tail": "金额", "type": "持仓", "description": "股票持仓金额" },
    { "head": "股票", "tail": "行业", "type": "所属", "description": "股票所属行业" },
    { "head": "股票", "tail": "所属国家或地区", "type": "所属", "description": "股票所属国家或地区" },
    { "head": "股票", "tail": "债券", "type": "持仓", "description": "股票持有某债券" },
    { "head": "股票", "tail": "可转债", "type": "持仓", "description": "股票持有某可转债" },
    { "head": "股票", "tail": "基金管理人", "type": "管理", "description": "股票由某机构管理" },
  ]
}

【待抽取文本】
{{INPUT_TEXT}}

"""