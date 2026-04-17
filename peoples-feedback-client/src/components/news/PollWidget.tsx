import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, BarChart3, Users, Loader2 } from "lucide-react";
import { newsApi } from "@/lib/api";
import type { PollItem } from "@/types/news";

export function PollWidget() {
  const queryClient = useQueryClient();
  const [votedPolls, setVotedPolls] = useState<number[]>(() => {
    try {
      const stored = sessionStorage.getItem("pf_voted_polls");
      return stored ? JSON.parse(stored) : [];
    } catch { return []; }
  });

  const { data: polls, isLoading } = useQuery<PollItem[]>({
    queryKey: ["polls"],
    queryFn: () => newsApi.getPolls(),
    staleTime: 60 * 1000,
  });

  const mutation = useMutation({
    mutationFn: ({ pollId, optionId }: { pollId: number; optionId: number }) =>
      newsApi.voteOnPoll(pollId, optionId),
    onSuccess: (_, variables) => {
      const updated = [...votedPolls, variables.pollId];
      setVotedPolls(updated);
      try { sessionStorage.setItem("pf_voted_polls", JSON.stringify(updated)); } catch {}
      queryClient.invalidateQueries({ queryKey: ["polls"] });
    },
  });

  if (isLoading) return (
    <div className="flex items-center justify-center py-16">
      <Loader2 className="w-8 h-8 animate-spin text-[var(--pf-saffron)]" />
    </div>
  );

  if (!polls?.length) return (
    <div className="text-center py-16 bg-white rounded-2xl border border-dashed border-zinc-200">
      <BarChart3 className="w-12 h-12 text-zinc-200 mx-auto mb-3" />
      <p className="text-zinc-400 font-medium">No active polls right now. Check back soon!</p>
    </div>
  );

  return (
    <div className="space-y-6">
      {polls.filter(p => p.is_active).map((poll) => {
        const hasVoted = votedPolls.includes(poll.id);
        const totalVotes = (poll.options || []).reduce(
          (sum, opt) => sum + (opt.votes_count || 0), 0
        );
        const isPending = mutation.isPending && mutation.variables?.pollId === poll.id;

        return (
          <div key={poll.id} className="bg-white rounded-2xl shadow-xl overflow-hidden border border-gray-100 p-6">
            <div className="flex items-center gap-2 mb-4">
              <div className="bg-gradient-to-br from-[var(--pf-saffron)] to-[var(--pf-orange)] text-white p-2 rounded-lg shadow-sm">
                <BarChart3 className="w-5 h-5" />
              </div>
              <h3 className="text-base font-black text-zinc-800 uppercase tracking-tight">Public Pulse Poll</h3>
              {poll.is_active && (
                <span className="ml-auto flex items-center gap-1.5 text-[10px] font-bold text-[var(--pf-green)] uppercase tracking-widest">
                  <span className="w-1.5 h-1.5 rounded-full bg-[var(--pf-green)] animate-pulse" />Live
                </span>
              )}
            </div>

            <p className="text-lg font-bold text-zinc-900 mb-5 leading-snug">{poll.question}</p>

            <div className="space-y-3">
              {(poll.options || []).map((opt) => {
                const percent = totalVotes > 0 ? Math.round((opt.votes_count / totalVotes) * 100) : 0;
                return (
                  <button key={opt.id} type="button"
                    disabled={hasVoted || isPending}
                    onClick={() => mutation.mutate({ pollId: poll.id, optionId: opt.id })}
                    className={`w-full relative group overflow-hidden rounded-xl border-2 transition-all p-4 text-left
                      ${hasVoted ? "border-gray-100 cursor-default" : "border-gray-200 hover:border-[var(--pf-saffron)] hover:bg-[var(--pf-saffron)]/5 active:scale-[0.99] cursor-pointer"}`}
                  >
                    {hasVoted && (
                      <div className="absolute inset-y-0 left-0 bg-gradient-to-r from-[var(--pf-navy)]/10 to-[var(--pf-navy)]/5 rounded-xl transition-all duration-1000"
                        style={{ width: `${percent}%` }} />
                    )}
                    <div className="relative flex items-center justify-between gap-3">
                      <span className={`font-semibold text-sm ${hasVoted ? "text-zinc-800" : "text-zinc-600 group-hover:text-zinc-900"}`}>
                        {opt.option_text}
                      </span>
                      {hasVoted && <span className="text-sm font-black text-[var(--pf-navy)] shrink-0">{percent}%</span>}
                      {!hasVoted && isPending && <Loader2 className="w-4 h-4 animate-spin text-[var(--pf-saffron)] shrink-0" />}
                    </div>
                  </button>
                );
              })}
            </div>

            <div className="mt-5 pt-5 border-t border-gray-100 flex items-center justify-between text-[10px] font-black uppercase tracking-widest text-zinc-400">
              <span className="flex items-center gap-1.5"><Users className="w-3.5 h-3.5" />{totalVotes.toLocaleString()} Votes</span>
              {hasVoted
                ? <span className="flex items-center gap-1.5 text-[var(--pf-green)]"><CheckCircle2 className="w-3.5 h-3.5" /> Vote Recorded</span>
                : <span className="text-[var(--pf-saffron)]">Cast Your Vote →</span>
              }
            </div>
          </div>
        );
      })}
    </div>
  );
}
