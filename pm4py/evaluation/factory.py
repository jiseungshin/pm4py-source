from pm4py.evaluation.generalization.versions import token_based as generalization_token_based
from pm4py.evaluation.precision.versions import etconformance_token as precision_token_based
from pm4py.evaluation.simplicity.versions import arc_degree as simplicity_arc_degree
from pm4py.evaluation.replay_fitness.versions import token_replay as fitness_token_based
from pm4py.algo.tokenreplay import factory as token_replay
from pm4py import log as log_lib

PARAM_ACTIVITY_KEY = 'activity_key'
PARAM_FITNESS_WEIGHT = 'fitness_weight'
PARAM_PRECISION_WEIGHT = 'precision_weight'
PARAM_SIMPLICITY_WEIGHT = 'simplicity_weight'
PARAM_GENERALIZATION_WEIGHT = 'generalization_weight'

PARAMETERS = [PARAM_ACTIVITY_KEY, PARAM_FITNESS_WEIGHT, PARAM_PRECISION_WEIGHT, PARAM_SIMPLICITY_WEIGHT, PARAM_GENERALIZATION_WEIGHT]

def apply_token_replay(log, net, initial_marking, final_marking, parameters=None):
    """
    Calculates all metrics based on token-based replay and returns a unified dictionary

    Parameters
    -----------
    log
        Trace log
    net
        Petri net
    initial_marking
        Initial marking
    final_marking
        Final marking
    parameters
        Parameters

    Returns
    -----------
    dictionary
        Dictionary containing fitness, precision, generalization and simplicity; along with the average weight of these metrics
    """
    if parameters is None:
        parameters = {}
    activity_key = parameters[PARAM_ACTIVITY_KEY] if PARAM_ACTIVITY_KEY in parameters else log_lib.util.xes.DEFAULT_NAME_KEY
    fitness_weight = parameters[PARAM_FITNESS_WEIGHT] if PARAM_FITNESS_WEIGHT in parameters else 0.25
    precision_weight = parameters[PARAM_PRECISION_WEIGHT] if PARAM_PRECISION_WEIGHT in parameters else 0.25
    simplicity_weight = parameters[PARAM_SIMPLICITY_WEIGHT] if PARAM_SIMPLICITY_WEIGHT in parameters else 0.25
    generalization_weight = parameters[PARAM_GENERALIZATION_WEIGHT] if PARAM_GENERALIZATION_WEIGHT in parameters else 0.25

    sum_of_weights = (fitness_weight + precision_weight + simplicity_weight + generalization_weight)
    fitness_weight = fitness_weight / sum_of_weights
    precision_weight = precision_weight / sum_of_weights
    simplicity_weight = simplicity_weight / sum_of_weights
    generalization_weight = generalization_weight / sum_of_weights

    [traceIsFit, traceFitnessValue, activatedTransitions, placeFitness, reachedMarkings, enabledTransitionsInMarkings] =\
        token_replay.apply(log, net, initial_marking, final_marking, activity_key=activity_key)

    parameters = {}
    parameters["activity_key"] = activity_key

    fitness = fitness_token_based.get_fitness(traceIsFit, traceFitnessValue)
    precision = precision_token_based.apply(log, net, initial_marking, final_marking, parameters=parameters)
    generalization = generalization_token_based.get_generalization(net, activatedTransitions)
    simplicity = simplicity_arc_degree.apply(net)

    dictionary = {}
    dictionary["fitness"] = fitness
    dictionary["precision"] = precision
    dictionary["generalization"] = generalization
    dictionary["simplicity"] = simplicity
    metricsAverageWeight = fitness_weight * fitness["averageFitness"] + precision_weight * precision\
                           + generalization_weight * generalization + simplicity_weight * simplicity
    dictionary["metricsAverageWeight"] = metricsAverageWeight

    return dictionary

TOKEN_BASED = "token_based"
VERSIONS = {TOKEN_BASED: apply_token_replay}

def apply(log, net, initial_marking, final_marking, parameters=None, variant="token_based"):
    return VERSIONS[variant](log, net, initial_marking, final_marking, parameters=parameters)