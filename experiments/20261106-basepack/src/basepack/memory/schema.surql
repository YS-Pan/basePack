DEFINE TABLE IF NOT EXISTS meta SCHEMALESS;
DEFINE TABLE IF NOT EXISTS source SCHEMALESS;
DEFINE INDEX IF NOT EXISTS source_path ON source FIELDS path UNIQUE;
DEFINE TABLE IF NOT EXISTS source_version SCHEMALESS;
DEFINE TABLE IF NOT EXISTS member SCHEMALESS;
DEFINE FIELD IF NOT EXISTS embedding ON member TYPE option<array<float>>;
DEFINE FIELD IF NOT EXISTS embedding_identity ON member TYPE option<string>;
DEFINE FIELD IF NOT EXISTS embedded_revision ON member TYPE option<string>;
DEFINE TABLE IF NOT EXISTS node SCHEMALESS;
DEFINE TABLE IF NOT EXISTS semantic TYPE NORMAL SCHEMALESS;
DEFINE TABLE IF NOT EXISTS graph_state TYPE NORMAL SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS status ON graph_state TYPE "current" | "historical" | "needs_review" | "retired";
DEFINE TABLE IF NOT EXISTS graph_edge TYPE RELATION IN knowledge_version | source_version | graph_edge OUT knowledge_version | source_version | graph_edge | member | node | source | semantic ENFORCED SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS type ON graph_edge TYPE "part_of" | "from_snapshot" | "has_basis" | "tests" | "supports" | "contradicts" | "implements" | "requires" | "uses" | "derived_from" | "version_of" | "supersedes" | "other";
DEFINE FIELD IF NOT EXISTS logical_id ON graph_edge TYPE option<record<semantic>>;
DEFINE FIELD IF NOT EXISTS knowledge_revision ON graph_edge TYPE option<string>;
DEFINE FIELD IF NOT EXISTS state ON graph_edge TYPE record<graph_state>;
DEFINE FIELD IF NOT EXISTS private ON graph_edge TYPE bool;
DEFINE FIELD IF NOT EXISTS scope_paths ON graph_edge TYPE array<string>;
DEFINE FIELD IF NOT EXISTS conditions ON graph_edge TYPE option<string | object> FLEXIBLE;
DEFINE FIELD IF NOT EXISTS text ON graph_edge TYPE option<string>;
DEFINE FIELD IF NOT EXISTS label ON graph_edge TYPE option<string>;
DEFINE FIELD IF NOT EXISTS locator ON graph_edge TYPE option<object> FLEXIBLE;
DEFINE INDEX IF NOT EXISTS graph_in_type ON graph_edge FIELDS in,type;
DEFINE INDEX IF NOT EXISTS graph_out_type ON graph_edge FIELDS out,type;
DEFINE INDEX IF NOT EXISTS graph_logical_revision ON graph_edge FIELDS logical_id,knowledge_revision;
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
DEFINE FUNCTION OVERWRITE fn::graph_state($exact: record) {
    RETURN type::record('graph_state', crypto::sha256(<string>$exact));
};
DEFINE FUNCTION OVERWRITE fn::knowledge_id($target: record, $revision: string) {
    RETURN type::record('knowledge_version', crypto::sha256(<string>$target + '\n' + $revision));
};
DEFINE FUNCTION OVERWRITE fn::retain_knowledge($record: object, $j_enter: option<int>) {
    IF $record.knowledge_revision != NONE {
        LET $key = fn::knowledge_id($record.id, $record.knowledge_revision);
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
