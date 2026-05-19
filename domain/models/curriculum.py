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
    ALGEBRA       = ("algebra",       Subject.MATH)
    CALCULUS      = ("calculus",      Subject.MATH)
    GEOMETRY      = ("geometry",      Subject.MATH)
    TRIGONOMETRY  = ("trigonometry",  Subject.MATH)
    PROBABILITY   = ("probability",   Subject.MATH)
    STATISTICS    = ("statistics",    Subject.MATH)

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

    # ALGEBRA
    LINEAR_EQUATIONS      = ("linear_equations",       Topic.ALGEBRA)
    QUADRATIC_EQUATIONS   = ("quadratic_equations",    Topic.ALGEBRA)
    POLYNOMIALS           = ("polynomials",            Topic.ALGEBRA)
    INEQUALITIES          = ("inequalities",           Topic.ALGEBRA)
    SYSTEMS_OF_EQUATIONS  = ("systems_of_equations",   Topic.ALGEBRA)

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

    # PROBABILITY
    BASIC_PROBABILITY     = ("basic_probability",      Topic.PROBABILITY)
    CONDITIONAL_PROB      = ("conditional_prob",       Topic.PROBABILITY)
    BAYES_THEOREM         = ("bayes_theorem",          Topic.PROBABILITY)
    DISTRIBUTIONS         = ("distributions",          Topic.PROBABILITY)

    # STATISTICS
    DESCRIPTIVE_STATS     = ("descriptive_stats",      Topic.STATISTICS)
    HYPOTHESIS_TESTING    = ("hypothesis_testing",     Topic.STATISTICS)
    REGRESSION            = ("regression",             Topic.STATISTICS)
    CONFIDENCE_INTERVALS  = ("confidence_intervals",   Topic.STATISTICS)

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


# ---------------------------------------------------------------------------
# Quick demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    c = Curriculum()

    # ✅ Valid path
    print(c.get(Subject.IT, Topic.ALGORITHMS, Concept.SORTING))

    # ✅ List helpers
    print("IT topics  :", [t.value for t in c.topics_of(Subject.IT)])
    print("ALGEBRA concepts:", [x.value for x in c.concepts_of(Topic.ALGEBRA)])

    # ❌ Topic not in Subject
    try:
        c.get(Subject.MATH, Topic.ALGORITHMS, Concept.SORTING)
    except ValueError as e:
        print("ValueError:", e)

    # ❌ Concept not in Topic
    try:
        c.get(Subject.IT, Topic.ALGORITHMS, Concept.DERIVATIVES)
    except ValueError as e:
        print("ValueError:", e)

    # ❌ Wrong type
    try:
        c.get("math", Topic.ALGEBRA, Concept.LINEAR_EQUATIONS)
    except TypeError as e:
        print("TypeError:", e)