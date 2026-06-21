from __future__ import annotations
from enum import Enum


# ---------------------------------------------------------------------------
# Subject
# ---------------------------------------------------------------------------

class Subject(str, Enum):
    MATH = "math"
    IT   = "it"


# ---------------------------------------------------------------------------
# Topic  — each member stores its parent Subject
# ---------------------------------------------------------------------------

class Topic(str, Enum):

    # --- MATH ---
    LINEAR_ALGEBRA      = ("linear_algebra",       Subject.MATH)
    CALCULUS            = ("calculus",             Subject.MATH)
    GEOMETRY            = ("geometry",             Subject.MATH)
    TRIGONOMETRY        = ("trigonometry",         Subject.MATH)
    PROBABILITY         = ("probability",          Subject.MATH)
    STATISTICS          = ("statistics",           Subject.MATH)
    DISCRETE_STRUCTURES = ("discrete_structures",  Subject.MATH)

    # --- IT ---
    PROGRAMMING     = ("programming",     Subject.IT)
    DATA_STRUCTURES = ("data_structures", Subject.IT)
    ALGORITHMS      = ("algorithms",      Subject.IT)
    DATABASES       = ("databases",       Subject.IT)

    def __new__(cls, value: str, subject: Subject):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.subject = subject
        return obj


# ---------------------------------------------------------------------------
# Concept  — each member stores its parent Topic
# ---------------------------------------------------------------------------

class Concept(str, Enum):

    # LINEAR_ALGEBRA
    VECTORS               = ("vectors",                Topic.LINEAR_ALGEBRA)
    MATRICES              = ("matrices",               Topic.LINEAR_ALGEBRA)
    DETERMINANTS          = ("determinants",           Topic.LINEAR_ALGEBRA)
    EIGENVALUES_EIGENVECTORS = ("eigenvalues_eigenvectors", Topic.LINEAR_ALGEBRA)
    LINEAR_TRANSFORMATIONS = ("linear_transformations", Topic.LINEAR_ALGEBRA)

    # CALCULUS
    LIMITS                = ("limits",                 Topic.CALCULUS)
    DERIVATIVES           = ("derivatives",            Topic.CALCULUS)
    INTEGRALS             = ("integrals",              Topic.CALCULUS)
    CHAIN_RULE            = ("chain_rule",             Topic.CALCULUS)
    TAYLOR_SERIES         = ("taylor_series",          Topic.CALCULUS)

    # GEOMETRY
    TRIANGLES             = ("triangles",              Topic.GEOMETRY)
    CIRCLES               = ("circles",                Topic.GEOMETRY)
    COORDINATE_GEOMETRY   = ("coordinate_geometry",    Topic.GEOMETRY)
    TRANSFORMATIONS       = ("transformations",        Topic.GEOMETRY)
    SOLID_GEOMETRY        = ("solid_geometry",         Topic.GEOMETRY)

    # TRIGONOMETRY
    TRIG_RATIOS           = ("trig_ratios",            Topic.TRIGONOMETRY)
    TRIG_IDENTITIES       = ("trig_identities",        Topic.TRIGONOMETRY)
    UNIT_CIRCLE           = ("unit_circle",            Topic.TRIGONOMETRY)
    INVERSE_TRIG          = ("inverse_trig",           Topic.TRIGONOMETRY)

    # PROBABILITY (Updated from Knowledge Tree)
    RANDOM_EXPERIMENT            = ("random_experiment",            Topic.PROBABILITY)
    SAMPLE_SPACE                 = ("sample_space",                 Topic.PROBABILITY)
    EVENT                        = ("event",                        Topic.PROBABILITY)
    MUTUALLY_EXCLUSIVE_EVENTS    = ("mutually_exclusive_events",    Topic.PROBABILITY)
    INDEPENDENT_EVENTS           = ("independent_events",           Topic.PROBABILITY)
    COMPLEMENTARY_EVENT          = ("complementary_event",          Topic.PROBABILITY)
    CLASSICAL_PROBABILITY        = ("classical_probability",        Topic.PROBABILITY)
    EMPIRICAL_PROBABILITY        = ("empirical_probability",        Topic.PROBABILITY)
    CONDITIONAL_PROBABILITY      = ("conditional_probability",      Topic.PROBABILITY)
    ADDITION_RULE                = ("addition_rule",                Topic.PROBABILITY)
    MULTIPLICATION_RULE          = ("multiplication_rule",          Topic.PROBABILITY)
    TOTAL_PROBABILITY_THEOREM    = ("total_probability_theorem",    Topic.PROBABILITY)
    BAYES_THEOREM                = ("bayes_theorem",                Topic.PROBABILITY)
    DISCRETE_RANDOM_VARIABLE     = ("discrete_random_variable",     Topic.PROBABILITY)
    CONTINUOUS_RANDOM_VARIABLE   = ("continuous_random_variable",   Topic.PROBABILITY)
    PROBABILITY_MASS_FUNCTION    = ("probability_mass_function",    Topic.PROBABILITY)
    PROBABILITY_DENSITY_FUNCTION = ("probability_density_function", Topic.PROBABILITY)
    CUMULATIVE_DISTRIBUTION_FUNC = ("cumulative_distribution_func", Topic.PROBABILITY)
    EXPECTED_VALUE               = ("expected_value",               Topic.PROBABILITY)
    VARIANCE                     = ("variance",                     Topic.PROBABILITY)
    STANDARD_DEVIATION           = ("standard_deviation",           Topic.PROBABILITY)
    MEDIAN_RV                    = ("median_rv",                    Topic.PROBABILITY)
    MODE_RV                      = ("mode_rv",                      Topic.PROBABILITY)
    BERNOULLI_DISTRIBUTION       = ("bernoulli_distribution",       Topic.PROBABILITY)
    BINOMIAL_DISTRIBUTION        = ("binomial_distribution",        Topic.PROBABILITY)
    POISSON_DISTRIBUTION         = ("poisson_distribution",         Topic.PROBABILITY)
    UNIFORM_DISTRIBUTION         = ("uniform_distribution",         Topic.PROBABILITY)
    NORMAL_DISTRIBUTION          = ("normal_distribution",          Topic.PROBABILITY)
    STANDARD_NORMAL_DIST         = ("standard_normal_dist",         Topic.PROBABILITY)
    EXPONENTIAL_DISTRIBUTION     = ("exponential_distribution",     Topic.PROBABILITY)
    LAW_OF_LARGE_NUMBERS         = ("law_of_large_numbers",         Topic.PROBABILITY)
    CENTRAL_LIMIT_THEOREM        = ("central_limit_theorem",        Topic.PROBABILITY)

    # STATISTICS (Updated from Knowledge Tree)
    POPULATION                   = ("population",                   Topic.STATISTICS)
    SAMPLE                       = ("sample",                       Topic.STATISTICS)
    SAMPLE_MEAN                  = ("sample_mean",                  Topic.STATISTICS)
    SAMPLE_VARIANCE              = ("sample_variance",              Topic.STATISTICS)
    ADJUSTED_SAMPLE_VARIANCE     = ("adjusted_sample_variance",     Topic.STATISTICS)
    POINT_ESTIMATION             = ("point_estimation",             Topic.STATISTICS)
    UNBIASEDNESS                 = ("unbiasedness",                 Topic.STATISTICS)
    CONFIDENCE_INTERVAL          = ("confidence_interval",          Topic.STATISTICS)
    CONFIDENCE_LEVEL             = ("confidence_level",             Topic.STATISTICS)
    MARGIN_OF_ERROR              = ("margin_of_error",              Topic.STATISTICS)
    NULL_HYPOTHESIS              = ("null_hypothesis",              Topic.STATISTICS)
    ALTERNATIVE_HYPOTHESIS       = ("alternative_hypothesis",       Topic.STATISTICS)
    TYPE_I_ERROR                 = ("type_i_error",                 Topic.STATISTICS)
    TYPE_II_ERROR                = ("type_ii_error",                Topic.STATISTICS)
    SIGNIFICANCE_LEVEL           = ("significance_level",           Topic.STATISTICS)
    P_VALUE                      = ("p_value",                      Topic.STATISTICS)
    CRITICAL_REGION              = ("critical_region",              Topic.STATISTICS)
    PEARSON_CORRELATION          = ("pearson_correlation",          Topic.STATISTICS)
    SIMPLE_LINEAR_REGRESSION     = ("simple_linear_regression",     Topic.STATISTICS)
    ORDINARY_LEAST_SQUARES       = ("ordinary_least_squares",       Topic.STATISTICS)
    COEFFICIENT_OF_DETERMINATION = ("coefficient_of_determination", Topic.STATISTICS)

    # DISCRETE_STRUCTURES (New Updated Branch)
    PROPOSITIONAL_LOGIC             = ("propositional_logic",          Topic.DISCRETE_STRUCTURES)
    LOGICAL_EQUIVALENCE             = ("logical_equivalence",          Topic.DISCRETE_STRUCTURES)
    PREDICATES_QUANTIFIERS          = ("predicates_quantifiers",       Topic.DISCRETE_STRUCTURES)
    RULES_OF_INFERENCE              = ("rules_of_inference",           Topic.DISCRETE_STRUCTURES)
    PROOF_METHODS                   = ("proof_methods",                Topic.DISCRETE_STRUCTURES)
    MATHEMATICAL_INDUCTION          = ("mathematical_induction",       Topic.DISCRETE_STRUCTURES)
    SET_THEORY_BASICS               = ("set_theory_basics",            Topic.DISCRETE_STRUCTURES)
    FUNCTION_MAPPINGS               = ("function_mappings",            Topic.DISCRETE_STRUCTURES)
    RELATION_PROPERTIES             = ("relation_properties",          Topic.DISCRETE_STRUCTURES)
    EQUIVALENCE_RELATIONS           = ("equivalence_relations",        Topic.DISCRETE_STRUCTURES)
    PARTIAL_ORDERS                  = ("partial_orders",               Topic.DISCRETE_STRUCTURES)
    COUNTING_PRINCIPLES             = ("counting_principles",          Topic.DISCRETE_STRUCTURES)
    PERMUTATIONS_COMBINATIONS       = ("permutations_combinations",    Topic.DISCRETE_STRUCTURES)
    PIGEONHOLE_PRINCIPLE            = ("pigeonhole_principle",         Topic.DISCRETE_STRUCTURES)
    INCLUSION_EXCLUSION             = ("inclusion_exclusion",          Topic.DISCRETE_STRUCTURES)
    RECURRENCE_RELATIONS            = ("recurrence_relations",         Topic.DISCRETE_STRUCTURES)
    GRAPH_MODELS                    = ("graph_models",                 Topic.DISCRETE_STRUCTURES)
    GRAPH_ISOMORPHISM               = ("graph_isomorphism",            Topic.DISCRETE_STRUCTURES)
    GRAPH_CONNECTIVITY              = ("graph_connectivity",           Topic.DISCRETE_STRUCTURES)
    EULER_HAMILTON_CIRCUITS         = ("euler_hamilton_circuits",      Topic.DISCRETE_STRUCTURES)
    MATHEMATICAL_TREE_PROPERTIES    = ("mathematical_tree_properties", Topic.DISCRETE_STRUCTURES)
    GRAPH_COLORING                  = ("graph_coloring",               Topic.DISCRETE_STRUCTURES)
    ALGEBRAIC_GROUPS                = ("algebraic_groups",             Topic.DISCRETE_STRUCTURES)
    RINGS_AND_FIELDS                = ("rings_and_fields",             Topic.DISCRETE_STRUCTURES)
    BOOLEAN_ALGEBRA_BASICS          = ("boolean_algebra_basics",       Topic.DISCRETE_STRUCTURES)

    # PROGRAMMING
    VARIABLES             = ("variables",              Topic.PROGRAMMING)
    CONTROL_FLOW          = ("control_flow",           Topic.PROGRAMMING)
    FUNCTIONS             = ("functions",              Topic.PROGRAMMING)
    OOP                   = ("oop",                    Topic.PROGRAMMING)
    RECURSION             = ("recursion",              Topic.PROGRAMMING)

    # DATA_STRUCTURES
    ARRAYS                = ("arrays",                 Topic.DATA_STRUCTURES)
    LINKED_LISTS          = ("linked_lists",           Topic.DATA_STRUCTURES)
    STACKS_QUEUES         = ("stacks_queues",          Topic.DATA_STRUCTURES)
    TREES                 = ("trees",                  Topic.DATA_STRUCTURES)
    GRAPHS                = ("graphs",                 Topic.DATA_STRUCTURES)
    HASH_TABLES           = ("hash_tables",            Topic.DATA_STRUCTURES)

    # ALGORITHMS
    BIG_O                 = ("big_o",                  Topic.ALGORITHMS)
    SORTING               = ("sorting",                Topic.ALGORITHMS)
    SEARCHING             = ("searching",              Topic.ALGORITHMS)
    DYNAMIC_PROGRAMMING   = ("dynamic_programming",    Topic.ALGORITHMS)
    GREEDY                = ("greedy",                 Topic.ALGORITHMS)

    # DATABASES
    RELATIONAL_MODEL      = ("relational_model",       Topic.DATABASES)
    SQL                   = ("sql",                    Topic.DATABASES)
    NORMALIZATION         = ("normalization",          Topic.DATABASES)
    INDEXING              = ("indexing",               Topic.DATABASES)
    TRANSACTIONS          = ("transactions",           Topic.DATABASES)

    def __new__(cls, value: str, topic: Topic):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.topic = topic
        return obj

    @property
    def subject(self) -> Subject:
        return self.topic.subject


# ---------------------------------------------------------------------------
# Curriculum — strict validated access
# ---------------------------------------------------------------------------

class Curriculum:
    """
    Access a concept by providing its full path: subject → topic → concept.
    Raises TypeError  if any argument is the wrong type.
    Raises ValueError if topic doesn't belong to subject,
                      or concept doesn't belong to topic.
    """

    def get(
        self,
        subject: Subject,
        topic: Topic,
        concept: Concept,
    ) -> dict:
        if not isinstance(subject, Subject):
            raise TypeError(
                f"Expected Subject, got {type(subject).__name__!r}."
            )
        if not isinstance(topic, Topic):
            raise TypeError(
                f"Expected Topic, got {type(topic).__name__!r}."
            )
        if not isinstance(concept, Concept):
            raise TypeError(
                f"Expected Concept, got {type(concept).__name__!r}."
            )

        if topic.subject is not subject:
            raise ValueError(
                f"Topic '{topic.value}' belongs to Subject '{topic.subject.value}', "
                f"not '{subject.value}'."
            )

        if concept.topic is not topic:
            raise ValueError(
                f"Concept '{concept.value}' belongs to Topic '{concept.topic.value}', "
                f"not '{topic.value}'."
            )

        return {
            "subject": subject.value,
            "topic":   topic.value,
            "concept": concept.value,
        }

    # -- convenience helpers ------------------------------------------------

    def topics_of(self, subject: Subject) -> list[Topic]:
        """Return all topics that belong to a given subject."""
        if not isinstance(subject, Subject):
            raise TypeError(f"Expected Subject, got {type(subject).__name__!r}.")
        return [t for t in Topic if t.subject is subject]

    def concepts_of(self, topic: Topic) -> list[Concept]:
        """Return all concepts that belong to a given topic."""
        if not isinstance(topic, Topic):
            raise TypeError(f"Expected Topic, got {type(topic).__name__!r}.")
        return [c for c in Concept if c.topic is topic]