# 拒绝误放在批次顶层的来源处置

0.10.0.dev1真实维护中，两份batch把dispositions放在顶层；程序返回成功却没有保存已阅处置，作者因而误判完成。现由CLI/Python共用_apply在编码前明确拒绝顶层dispositions和deferred_refinement，提示放入对应sources[]；不自动搬移输入。

隔离红测复现静默接受。修复后真实数据库与CLI定向60passed、0skipped，覆盖填值/空/null、自动/显式owner、编码前拒绝、六表无半批及原有合法B/F；独立客户端安装后核50包文件与源码/wheel一致。两份作者纠正稿已成功发布，持久反馈已fixed。

本项目仍用0.10.0.dev1开发版，最终wheel由哈希及提交区分，未变schema、原库、owner或共享服务。原证和实际使用过程见[实施结果](../../tasks/20261106-memory-system/maintenance-implementation-result.md)。
