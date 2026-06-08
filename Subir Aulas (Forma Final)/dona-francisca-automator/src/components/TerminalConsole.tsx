import React, { useRef, useEffect } from 'react';
import { LogEntry, AutomationState } from '../types';
import { Terminal, Copy, Trash2, Download, Play, Pause } from 'lucide-react';

interface TerminalConsoleProps {
  logs: LogEntry[];
  automationState: AutomationState;
  onClearLogs: () => void;
  autoScroll: boolean;
  onToggleAutoScroll: () => void;
}

export default function TerminalConsole({
  logs,
  automationState,
  onClearLogs,
  autoScroll,
  onToggleAutoScroll,
}: TerminalConsoleProps) {
  const terminalEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoScroll && terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  const copyToClipboard = () => {
    const text = logs
      .map((log) => `[${log.timestamp}] ${log.level} - ${log.message}`)
      .join('\n');
    navigator.clipboard.writeText(text);
    alert('Logs copiados para a área de transferência!');
  };

  const downloadLogs = () => {
    const text = logs
      .map((log) => `[${log.timestamp}] ${log.level} - ${log.message}`)
      .join('\n');
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `logs_automacao_${Date.now()}.txt`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const getStatusColor = () => {
    switch (automationState) {
      case 'IDLE':
        return { text: 'SYSTEM STABLE', bg: 'bg-[#00ff66]/10', border: 'border-[#00ff66]/20', dot: 'bg-[#00ff66]' };
      case 'PREPARED':
        return { text: 'ROBOT ARMED', bg: 'bg-cyan-500/10', border: 'border-cyan-500/20', dot: 'bg-cyan-400' };
      case 'MIGRATING':
        return { text: 'AUTOMATION ACTIVE', bg: 'bg-[#00f0ff]/15', border: 'border-[#00f0ff]/30', dot: 'animate-ping bg-[#00f0ff]' };
      case 'PAUSED':
        return { text: 'AUTOMATION PAUSED', bg: 'bg-amber-400/10', border: 'border-amber-400/20', dot: 'bg-amber-400' };
      case 'COMPLETED':
        return { text: 'MIGRATION COMPLETE', bg: 'bg-emerald-500/15', border: 'border-emerald-500/30', dot: 'bg-emerald-400' };
    }
  };

  const status = getStatusColor();

  return (
    <div id="terminal-section" className="bg-[#0f141c] border border-slate-800 rounded-xl overflow-hidden shadow-2xl flex flex-col h-[320px]">
      {/* Logger Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between px-4 py-3 bg-[#131b26] border-b border-slate-800 gap-2">
        <div className="flex items-center gap-3">
          <div className="flex space-x-1.5">
            <span className="w-3 h-3 rounded-full bg-red-500/40" />
            <span className="w-3 h-3 rounded-full bg-yellow-500/40" />
            <span className="w-3 h-3 rounded-full bg-green-500/40" />
          </div>
          <div className="h-4 w-[1px] bg-slate-800" />
          <div className="flex items-center gap-2">
            <Terminal className="w-4 h-4 text-cyan-400" />
            <span className="text-xs font-mono font-medium text-slate-300">CONSOLE DE SAÍDA DO ROBÔ</span>
          </div>

          <div className={`flex items-center gap-2 px-2.5 py-0.5 rounded-full border text-[10px] font-mono tracking-wider font-semibold ${status.bg} ${status.border}`}>
            <span className="relative flex h-2 w-2">
              <span className={`absolute inline-flex h-full w-full rounded-full opacity-75 ${status.dot}`}></span>
              <span className={`relative inline-flex rounded-full h-2 w-2 ${status.dot.replace('animate-ping ', '')}`}></span>
            </span>
            <span className="text-slate-200">{status.text}</span>
          </div>
        </div>

        {/* Toolbar Actions */}
        <div className="flex items-center gap-1">
          <button
            onClick={onToggleAutoScroll}
            title={autoScroll ? "Pausar rolagem automática" : "Ativar rolagem automática"}
            className={`p-1.5 rounded transition duration-200 ${
              autoScroll ? 'text-cyan-400 hover:bg-cyan-950/40' : 'text-slate-500 hover:bg-slate-800'
            }`}
          >
            {autoScroll ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
          </button>
          
          <button
            onClick={copyToClipboard}
            title="Copiar logs"
            className="p-1.5 text-slate-400 hover:text-cyan-400 hover:bg-[#1f2836] rounded transition duration-200"
          >
            <Copy className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={downloadLogs}
            title="Download logs"
            className="p-1.5 text-slate-400 hover:text-cyan-400 hover:bg-[#1f2836] rounded transition duration-200"
          >
            <Download className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={onClearLogs}
            title="Limpar console"
            className="p-1.5 text-slate-400 hover:text-red-400 hover:bg-[#1f2836] rounded transition duration-200"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Terminal Screen lines */}
      <div className="flex-1 font-mono text-xs overflow-y-auto p-4 space-y-1.5 bg-[#0b0f14] text-slate-300 antialiased selection:bg-cyan-500/30 selection:text-white">
        {logs.length === 0 ? (
          <div className="h-full flex items-center justify-center text-slate-600 italic">
            Nenhum log gerado ainda. Clique em 'PREPARAR ROBÔ' ou 'COMEÇAR AUTOMAÇÃO' para iniciar.
          </div>
        ) : (
          logs.map((log) => {
            let labelColor = 'text-cyan-400';
            if (log.level === 'SUCCESS') labelColor = 'text-green-400 font-bold';
            if (log.level === 'WARNING') labelColor = 'text-yellow-400';
            if (log.level === 'ERROR') labelColor = 'text-red-400 font-bold';

            return (
              <div key={log.id} className="flex items-start gap-1 p-0.5 rounded hover:bg-slate-900/60 transition-colors">
                <span className="text-slate-600 shrink-0 select-none">[{log.timestamp}]</span>
                <span className={`w-16 ${labelColor} font-semibold shrink-0`}>{log.level}</span>
                <span className="text-slate-50 shrink-0 select-none">-</span>
                <span className="text-slate-300 break-all pl-1">{log.message}</span>
              </div>
            );
          })
        )}
        <div ref={terminalEndRef} />
      </div>
    </div>
  );
}
