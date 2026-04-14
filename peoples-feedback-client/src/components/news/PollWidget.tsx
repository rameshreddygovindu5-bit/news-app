import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, BarChart3, Users } from "lucide-react";
import { newsApi } from "@/lib/api";

// Fetch polls (mock or API)
const fetchPolls = async () => {
  const res = await fetch(`${import.meta.env.VITE_API_URL}/api/polls/`);
  if (!res.ok) return [];
  return res.json();
};

const submitVote = async ({ pollId, optionId }: { pollId: number; optionId: number }) => {
  const res = await fetch(`${import.meta.env.VITE_API_URL}/api/polls/${pollId}/vote`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ option_id: optionId }),
  });
  return res.json();
};

export function PollWidget() {
  const queryClient = useQueryClient();
  const [votedPolls, setVotedPolls] = useState<number[]>([]);

  const { data: polls, isLoading } = useQuery({
    queryKey: ["polls"],
    queryFn: fetchPolls,
  });

  const mutation = useMutation({
    mutationFn: submitVote,
    onSuccess: (_, variables) => {
      setVotedPolls(prev => [...prev, variables.pollId]);
      queryClient.invalidateQueries({ queryKey: ["polls"] });
    },
  });

  if (isLoading) return <div className="text-center py-20"><div className="spinner mx-auto" /></div>;

  if (!polls?.length) return (
    <div className="text-center py-16 bg-white rounded-2xl border border-dashed border-zinc-200">
      <BarChart3 className="w-12 h-12 text-zinc-200 mx-auto mb-3" />
      <p className="text-zinc-400 font-medium">No active polls at the moment. Check back soon!</p>
    </div>
  );

  return (
    <div className="space-y-6">
      {polls.map((poll: any) => {
        const hasVoted = votedPolls.includes(poll.id);
        const totalVotes = poll.options.reduce((sum: number, opt: any) => sum + opt.votes_count, 0);

        return (
          <div key={poll.id} className="bg-white rounded-2xl shadow-xl overflow-hidden border border-gray-100 p-6">
            <div className="flex items-center gap-2 mb-4">
              <div className="bg-[var(--pf-saffron)] text-white p-2 rounded-lg">
                <BarChart3 className="w-5 h-5" />
              </div>
              <h3 className="text-xl font-black text-zinc-800 uppercase tracking-tight">Public Pulse Poll</h3>
            </div>
            
            <p className="text-lg font-bold text-zinc-900 mb-6 leading-tight">{poll.question}</p>
            
            <div className="space-y-3">
              {poll.options.map((opt: any) => {
                const percent = totalVotes > 0 ? Math.round((opt.votes_count / totalVotes) * 100) : 0;
                
                return (
                  <button
                    key={opt.id}
                    disabled={hasVoted || mutation.isPending}
                    onClick={() => mutation.mutate({ pollId: poll.id, optionId: opt.id })}
                    className={`w-full relative group overflow-hidden rounded-xl border-2 transition-all p-4 text-left
                      ${hasVoted 
                        ? 'border-gray-100 cursor-default' 
                        : 'border-gray-100 hover:border-[var(--pf-saffron)] hover:bg-[var(--pf-saffron)]/5'}`}
                  >
                    {/* Progress bar background */}
                    {hasVoted && (
                      <div 
                        className="absolute inset-0 bg-gradient-to-r from-[var(--pf-navy)]/10 to-[var(--pf-navy)]/5 transition-all duration-1000"
                        style={{ width: `${percent}%` }}
                      />
                    )}
                    
                    <div className="relative flex items-center justify-between">
                      <span className={`font-bold ${hasVoted ? 'text-zinc-800' : 'text-zinc-600 group-hover:text-zinc-900'}`}>
                        {opt.option_text}
                      </span>
                      {hasVoted && (
                        <span className="text-sm font-black text-[var(--pf-navy)]">{percent}%</span>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>

            <div className="mt-6 pt-6 border-t border-gray-100 flex items-center justify-between text-[10px] font-black uppercase tracking-widest text-zinc-400">
              <span className="flex items-center gap-1.5">
                <Users className="w-3.5 h-3.5" /> {totalVotes.toLocaleString()} Votes
              </span>
              {hasVoted ? (
                <span className="flex items-center gap-1.5 text-[var(--pf-green)]">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Vote Recorded
                </span>
              ) : (
                <span>Voting Ends Soon</span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
