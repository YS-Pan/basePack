# 直接采用每个worker自己的宿主派工参数

实际0.17.3维护中，布局与渲染均正确要求Luna/max，发布协调者却将四名reader显式派成Terra/ultra；独立实际模型记录证实后已停组并保存已接受内容与未发布稿。0.17.4在既有dispatch增加完整spawn_arguments，统一bootstrap同源生成；协调者直接采用该worker对象，避免手工拆字段后套用自身参数。未改变原descriptor、render_command或行为/并发合同，不构成宿主模型的硬强制。

普通安装66文件三方一致、pip check通过；最终139项现有测试和142项安装/渲染静态检查通过。真实新身份8–12来源小批验收另行核实际model/effort，字段打印成功不替代实际派工。记录及原错见[执行记录](../../tasks/20261115-real-use-rectification/execution.md#阶段1实际模型误派与0174修正)和[用量调查](../../tasks/20261115-real-use-rectification/research/terra-usage-20261117.md)。
