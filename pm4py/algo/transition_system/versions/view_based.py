from pm4py.log import util as log_util
from pm4py.models.transition_system import transition_system as ts
import collections

VIEW_MULTI_SET = 'multiset'
VIEW_SET = 'set'
VIEW_SEQUENCE = 'sequence'

VIEWS = {VIEW_MULTI_SET, VIEW_SET, VIEW_SEQUENCE}

DIRECTION_FORWARD = 'forward'
DIRECTION_BACKWARD = 'backward'
DIRECTIONS = {DIRECTION_FORWARD, DIRECTION_BACKWARD}

PARAM_KEY_VIEW = 'view'
PARAM_KEY_WINDOW = 'window'
PARAM_KEY_DIRECTION = 'direction'
DEFAULT_PARAMETERS = {PARAM_KEY_VIEW: VIEW_MULTI_SET, PARAM_KEY_WINDOW: 5, PARAM_KEY_DIRECTION: DIRECTION_FORWARD}


def apply(trace_log, parameters=DEFAULT_PARAMETERS, activity_key=log_util.xes.DEFAULT_NAME_KEY):
    transition_system = ts.TransitionSystem()
    control_flow_log = log_util.trace_log.project_traces(trace_log, activity_key)
    l = (list(map(lambda t: __compute_view_sequence(t, parameters), control_flow_log)))
    for vs in l:
        __construct_state_path(vs, transition_system)
    return transition_system


def __construct_state_path(view_sequence, transition_system):
    for i in range(0, len(view_sequence) - 1):
        sf = {'state': s for s in transition_system.states if s.name == view_sequence[i][0]}
        sf = sf['state'] if len(sf) > 0 else ts.TransitionSystem.State(view_sequence[i][0])
        st = {'state': s for s in transition_system.states if s.name == view_sequence[i + 1][0]}
        st = st['state'] if len(st) > 0 else ts.TransitionSystem.State(view_sequence[i + 1][0])
        t = {'t': t for t in sf.outgoing if t.name == view_sequence[i][1] and t.from_state == sf and t.to_state == st}
        if len(t) == 0:
            t = ts.TransitionSystem.Transition(view_sequence[i][1], sf, st)
            sf.outgoing.add(t)
            st.incoming.add(t)
        else:
            t = t['t']
        transition_system.states.add(sf)
        transition_system.states.add(st)
        transition_system.transitions.add(t)


def __compute_view_sequence(trace, parameters):
    view_sequences = list()
    for i in range(0, len(trace) + 1):
        if parameters[PARAM_KEY_DIRECTION] == DIRECTION_FORWARD:
            view_sequences.append((__apply_abstr(trace[i:i+parameters[PARAM_KEY_WINDOW]], parameters), trace[i] if i < len(trace) else None))
        else:
            view_sequences.append((__apply_abstr(trace[max(0, i - parameters[PARAM_KEY_WINDOW]):i], parameters), trace[i] if i < len(trace) else None))
    return view_sequences


def __apply_abstr(seq, parameters):
    case = {
        VIEW_SEQUENCE: list,
        VIEW_MULTI_SET: collections.Counter,
        VIEW_SET: set
    }
    return case[parameters[PARAM_KEY_VIEW]](seq) if len(seq) > 0 else case[parameters[PARAM_KEY_VIEW]]()
