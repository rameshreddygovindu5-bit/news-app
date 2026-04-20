import React from 'react';

export function FlagBadge({flag}) {
  const m={
    P:['PENDING','badge-paused'],
    N:['NEW','badge-new'],
    A:['AI DONE','badge-processed'],
    Y:['TOP','badge-top'],
    D:['DEL','badge-deleted']
  };
  const [l,cl]=m[flag]||['?',''];
  return <span className={`badge ${cl}`}>{l}</span>;
}

export function StatusBadge({status}) {
  const cl = {
    'DONE':'badge-enabled',
    'completed':'badge-enabled',
    'RUNNING':'badge-new',
    'running':'badge-new',
    'PARTIAL':'badge-paused',
    'FAILED':'badge-deleted',
    'failed':'badge-deleted'
  }[status]||'badge-new';
  return <span className={`badge ${cl}`}>{status}</span>;
}
