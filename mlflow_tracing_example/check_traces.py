"""Shows the problem: chat traces and search traces are separate, unlinked traces."""
import mlflow

from config import EXPERIMENT, setup_mlflow

setup_mlflow()
exp = mlflow.get_experiment_by_name(EXPERIMENT)
traces = mlflow.search_traces(locations=[exp.experiment_id], return_type="list")

def root_name(t):
    return next(s.name for s in t.data.spans if s.parent_id is None)


chat = [t for t in traces if root_name(t) == "chat_turn"]
search = [t for t in traces if t not in chat]

print(f"Total traces: {len(traces)}  (chat: {len(chat)}, search: {len(search)})\n")
for label, group in (("CHAT", chat), ("SEARCH", search)):
    for t in sorted(group, key=lambda t: t.info.timestamp_ms):
        names = [s.name for s in t.data.spans]
        print(f"[{label:6}] {t.info.trace_id}  spans={len(names):2}  {', '.join(names[:6])}")

print("\nGOAL: 1 chat_turn trace each, with search_agent spans nested inside the "
      "turns that called the tool (and none for turns that didn't).")