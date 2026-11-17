DEFINE TABLE IF NOT EXISTS meta SCHEMALESS;
DEFINE TABLE IF NOT EXISTS source SCHEMALESS;
DEFINE INDEX IF NOT EXISTS source_path ON source FIELDS path UNIQUE;
DEFINE TABLE IF NOT EXISTS source_version SCHEMALESS;
DEFINE TABLE IF NOT EXISTS member SCHEMALESS;
DEFINE FIELD IF NOT EXISTS embedding ON member TYPE option<array<float>>;
DEFINE FIELD IF NOT EXISTS embedding_identity ON member TYPE option<string>;
DEFINE FIELD IF NOT EXISTS embedded_revision ON member TYPE option<string>;
DEFINE TABLE IF NOT EXISTS node SCHEMALESS;
DEFINE TABLE IF NOT EXISTS semantic TYPE RELATION IN member | node OUT member | node ENFORCED SCHEMALESS;
DEFINE TABLE IF NOT EXISTS change SCHEMALESS;
DEFINE TABLE IF NOT EXISTS knowledge_version SCHEMALESS;
DEFINE INDEX IF NOT EXISTS knowledge_identity ON knowledge_version FIELDS target,knowledge_revision UNIQUE;
DEFINE TABLE IF NOT EXISTS access_state SCHEMALESS;
DEFINE TABLE IF NOT EXISTS delivery SCHEMALESS;
DEFINE TABLE IF NOT EXISTS behavior_model SCHEMALESS;
DEFINE TABLE IF NOT EXISTS behavior_projection SCHEMALESS;
DEFINE TABLE IF NOT EXISTS behavior_mass SCHEMALESS;
DEFINE TABLE IF NOT EXISTS behavior_version SCHEMALESS;
DEFINE INDEX IF NOT EXISTS delivery_j ON delivery FIELDS j;
DEFINE INDEX IF NOT EXISTS knowledge_j_enter ON knowledge_version FIELDS j_enter;
DEFINE INDEX IF NOT EXISTS behavior_version_generation_target ON behavior_version FIELDS generation,target;
DEFINE INDEX IF NOT EXISTS behavior_mass_generation ON behavior_mass FIELDS generation;
DEFINE FUNCTION OVERWRITE fn::retain_knowledge($record: object, $j_enter: option<int>) {
    IF $record.knowledge_revision != NONE {
        LET $key = type::record('knowledge_version', crypto::sha256(<string>$record.id + '\n' + $record.knowledge_revision));
        IF $key.id = NONE {
            CREATE $key CONTENT {target:$record.id, knowledge_revision:$record.knowledge_revision,
                record:object::remove($record, 'embedding'), j_enter:$j_enter};
        };
    };
};
DEFINE EVENT OVERWRITE retain_member_version ON member
    WHEN $before.knowledge_revision != $after.knowledge_revision THEN {
        IF $before != NONE { fn::retain_knowledge($before, NONE); };
        IF $after != NONE { fn::retain_knowledge($after, (meta:delivery.j ?? 0)); };
    };
DEFINE EVENT OVERWRITE retain_node_version ON node
    WHEN $before.knowledge_revision != $after.knowledge_revision THEN {
        IF $before != NONE { fn::retain_knowledge($before, NONE); };
        IF $after != NONE { fn::retain_knowledge($after, (meta:delivery.j ?? 0)); };
    };
DEFINE EVENT OVERWRITE retain_semantic_version ON semantic
    WHEN $before.knowledge_revision != $after.knowledge_revision THEN {
        IF $before != NONE { fn::retain_knowledge($before, NONE); };
        IF $after != NONE { fn::retain_knowledge($after, (meta:delivery.j ?? 0)); };
    };
DEFINE ANALYZER IF NOT EXISTS memory_zh TOKENIZERS blank,class,segment(chinese) FILTERS lowercase;
DEFINE INDEX IF NOT EXISTS member_text ON member FIELDS text FULLTEXT ANALYZER memory_zh BM25;
DEFINE INDEX IF NOT EXISTS member_title ON member FIELDS title FULLTEXT ANALYZER memory_zh BM25;
DEFINE TABLE IF NOT EXISTS feedback SCHEMALESS;
