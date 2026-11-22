DEFINE TABLE graph_object SCHEMAFULL TYPE NORMAL;
DEFINE FIELD head ON graph_object TYPE option<record<graph_version | graph_snapshot | graph_edge>>;

DEFINE TABLE graph_version SCHEMAFULL TYPE NORMAL;
DEFINE FIELD text ON graph_version TYPE string;

DEFINE TABLE graph_snapshot SCHEMAFULL TYPE NORMAL;
DEFINE FIELD path ON graph_snapshot TYPE string;
DEFINE FIELD text ON graph_snapshot TYPE string;

DEFINE TABLE graph_edge SCHEMAFULL TYPE RELATION
    IN graph_object | graph_version | graph_snapshot | graph_edge
    OUT graph_object | graph_version | graph_snapshot | graph_edge ENFORCED;
DEFINE FIELD type ON graph_edge TYPE string ASSERT $value IN [
    'part_of', 'from_snapshot', 'has_basis', 'tests', 'supports', 'contradicts',
    'implements', 'requires', 'uses', 'derived_from', 'version_of', 'supersedes', 'other'
];
DEFINE FIELD condition ON graph_edge TYPE option<string>;
DEFINE FIELD line ON graph_edge TYPE option<int> ASSERT $value = NONE OR $value > 0;
DEFINE FIELD phrase ON graph_edge TYPE option<string> ASSERT $this.type != 'other' OR $value != NONE;

-- Ordinary and filtered directional reads can use the same stored edge records.
DEFINE INDEX outgoing ON graph_edge FIELDS in, type;
DEFINE INDEX incoming ON graph_edge FIELDS out, type;

DEFINE TABLE graph_publication SCHEMAFULL TYPE NORMAL;
DEFINE FIELD claim ON graph_publication TYPE record<graph_version>;
