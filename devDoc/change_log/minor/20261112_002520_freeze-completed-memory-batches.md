# 维护批次按最终稿和唯一快照交接

真实维护中，作者仍在补第4行依据和摘要引用时，旧稿已被提交并返回42成员成功；后补内容未进入该批。协调者将来源改回partial，经当前版本补齐后，feedback:a832017a712a4e6ca359e0ce70d0b5b0已fixed。

协调者模板现要求作者明确完成该batch后才接收，记录最终路径/hash；后续修订另存并重新prepare。发布者冻结唯一自有字节快照、记录hash并提交该快照，避免使用作者仍会改动的路径。该规则已传给本轮所有分支，后续A170、A180及B追加批实际依此发布；不追加语义复审。

模板渲染回归15passed。无逻辑/API/schema变更；随最终wheel交付，实际安装哈希及本轮维护结果见[实施结果](../../tasks/20261106-memory-system/maintenance-implementation-result.md)。
