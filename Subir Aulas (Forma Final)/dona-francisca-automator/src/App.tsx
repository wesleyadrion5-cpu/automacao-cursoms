import React, { useState, useEffect, useRef } from 'react';
import { MappedRow, LogEntry, AutomationState } from './types';
import TerminalConsole from './components/TerminalConsole';
import StatusCard from './components/StatusCard';
import SpreadsheetLoader from './components/SpreadsheetLoader';
import PythonCodeHub from './components/PythonCodeHub';
import {
  Home,
  Bot,
  Play,
  Pause,
  RotateCcw,
  Settings,
  Minimize2,
  Maximize2,
  X,
  Code,
  Sliders,
  Sparkles,
  HelpCircle
} from 'lucide-react';

const API_BASE = window.location.port === '3000' ? 'http://localhost:5000' : '';

export default function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'python'>('dashboard');
  const [rows, setRows] = useState<MappedRow[]>([]);
  const [processedCount, setProcessedCount] = useState(0);
  const [progressPercent, setProgressPercent] = useState(0);
  const [automationState, setAutomationState] = useState<AutomationState>('IDLE');
  const [columnMapping, setColumnMapping] = useState({
    modulo: 'NOMES MAPEADOS',
    video: 'MÍDIA / VÍDEO',
    duracao: 'DURAÇÃO',
    extra: 'FASES',
  });
  
  const [robotName, setRobotName] = useState('Robô 1');
  const [delay, setDelay] = useState(1500); // milliseconds
  const [autoScrollLogs, setAutoScrollLogs] = useState(true);
  const [logs, setLogs] = useState<LogEntry[]>([]);

  // Carrega as linhas iniciais do Python ao iniciar a página e inicia o polling
  useEffect(() => {
    const fetchInitialRows = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/rows`);
        if (res.ok) {
          const data = await res.json();
          if (data && data.length > 0) {
            setRows(data);
          }
        }
      } catch (err) {
        console.error("Erro ao buscar registros iniciais do Python:", err);
      }
    };

    const fetchConfig = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/config`);
        if (res.ok) {
          const config = await res.json();
          if (config.robot_name) setRobotName(config.robot_name);
          if (config.delay_between_steps) setDelay(config.delay_between_steps);
        }
      } catch (err) {
        console.error("Erro ao buscar configurações do Python:", err);
      }
    };

    fetchInitialRows();
    fetchConfig();

    const interval = setInterval(async () => {
      try {
        // 1. Estatísticas e Estados
        const resStats = await fetch(`${API_BASE}/api/stats`);
        if (resStats.ok) {
          const stats = await resStats.json();
          setAutomationState(stats.state as AutomationState);
          setProcessedCount(stats.concluidos);
          if (stats.total > 0) {
            setProgressPercent(Math.round((stats.concluidos / stats.total) * 100));
          } else {
            setProgressPercent(0);
          }
          // Sincroniza o tamanho da fila local caso o Python tenha carregado dados por fora
          if (stats.total > 0 && rows.length !== stats.total && stats.total !== 10) { 
            const resRows = await fetch(`${API_BASE}/api/rows`);
            if (resRows.ok) {
              const dataRows = await resRows.json();
              setRows(dataRows);
            }
          }
        }

        // 2. Logs do Terminal
        const resLogs = await fetch(`${API_BASE}/api/logs`);
        if (resLogs.ok) {
          const logsData = await resLogs.json();
          setLogs(logsData);
        }
      } catch (err) {
        console.warn("Monitor remoto sem conexão com o Flask do Python:", err);
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [rows.length]);

  const addLog = (level: 'INFO' | 'SUCCESS' | 'WARNING' | 'ERROR', message: string) => {
    const timestamp = new Date().toLocaleTimeString('pt-BR', { hour12: false });
    const newLog: LogEntry = {
      id: String(Date.now()) + Math.random().toString(36).substring(2, 5),
      timestamp,
      level,
      message,
    };
    setLogs((prev) => [...prev, newLog]);
  };

  // Toda vez que as linhas de controle local mudarem, envia para o backend do Python
  const handleRowsChange = async (newRows: MappedRow[]) => {
    setRows(newRows);
    try {
      const res = await fetch(`${API_BASE}/api/rows`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ rows: newRows }),
      });
      if (!res.ok) {
        console.error("Falha ao sincronizar planilha com o Python:", res.statusText);
      }
    } catch (err) {
      console.error("Erro de rede ao sincronizar planilha:", err);
    }
  };

  // Robot Action 1: Prepara o Robô no Python
  const handlePrepareRobot = async () => {
    if (rows.length === 0) {
      addLog('ERROR', 'Impossível carregar. Nenhuma planilha ou arquivo mapeado carregado.');
      return;
    }
    try {
      addLog('INFO', `[${robotName}] Solicitando preparação ao robô Python...`);
      const res = await fetch(`${API_BASE}/api/prepare`, { method: 'POST' });
      if (res.ok) {
        setAutomationState('PREPARED');
      } else {
        const errData = await res.json();
        addLog('ERROR', `Erro ao preparar: ${errData.error || res.statusText}`);
      }
    } catch (err: any) {
      addLog('ERROR', `Erro de conexão ao preparar o robô: ${err.message}`);
    }
  };

  // Robot Action 2: Começar / Pausar Automação no Python
  const handleStartAutomation = async () => {
    if (rows.length === 0) {
      addLog('ERROR', 'Falha ao iniciar automação: carregue uma planilha antes de começar.');
      return;
    }

    try {
      if (automationState === 'MIGRATING') {
        // Pausar
        addLog('INFO', `[${robotName}] Enviando solicitação de pausa...`);
        const res = await fetch(`${API_BASE}/api/pause`, { method: 'POST' });
        if (res.ok) {
          setAutomationState('PAUSED');
        } else {
          addLog('ERROR', 'Falha ao pausar a automação.');
        }
      } else {
        // Começar ou Retomar
        addLog('INFO', `[${robotName}] Solicitando início da automação...`);
        const res = await fetch(`${API_BASE}/api/start`, { method: 'POST' });
        if (res.ok) {
          setAutomationState('MIGRATING');
        } else {
          addLog('ERROR', 'Falha ao iniciar a automação.');
        }
      }
    } catch (err: any) {
      addLog('ERROR', `Falha de rede na ação de automação: ${err.message}`);
    }
  };

  // Robot Action 3: Redefinir Estado
  const handleResetRobot = async () => {
    try {
      addLog('INFO', `[${robotName}] Enviando comando de reset...`);
      const res = await fetch(`${API_BASE}/api/reset`, { method: 'POST' });
      if (res.ok) {
        setRows([]);
        setProcessedCount(0);
        setProgressPercent(0);
        setAutomationState('IDLE');
      } else {
        addLog('ERROR', 'Falha ao resetar o robô.');
      }
    } catch (err: any) {
      addLog('ERROR', `Falha de rede ao resetar o robô: ${err.message}`);
    }
  };

  return (
    <div className="min-h-screen bg-[#0d131a] text-slate-100 flex flex-col font-sans transition-colors duration-300">
      
      {/* OS App mock Header title bar */}
      <header className="bg-[#0b0f14] border-b border-slate-900 px-4 py-2.5 flex items-center justify-between shrink-0 select-none">
        <div className="flex items-center gap-3">
          {/* Cyan pulsing dot */}
          <div className="flex items-center justify-center bg-cyan-950/40 p-1.5 rounded-lg border border-cyan-800/30 text-[#00f2fe]">
            <Bot className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <h1 className="text-sm font-sans font-extrabold tracking-wide text-slate-100">
              Dona Francisca
            </h1>
            <p className="text-[10px] font-mono tracking-wider text-cyan-400 font-bold uppercase leading-tight">
              Automação de módulos Mapeados
            </p>
          </div>
        </div>

        {/* Outer window controls mockup */}
        <div className="flex items-center gap-4 text-slate-500">
          <div className="flex items-center gap-1">
            <button className="p-1 hover:text-slate-300 hover:bg-slate-800/40 rounded transition">
              <Settings className="w-4 h-4" />
            </button>
            <button className="p-1 hover:text-slate-300 hover:bg-slate-800/40 rounded transition">
              <Minimize2 className="w-3.5 h-3.5" />
            </button>
            <button className="p-1 hover:text-slate-300 hover:bg-slate-800/40 rounded transition">
              <Maximize2 className="w-3.5 h-3.5" />
            </button>
            <button className="p-1 hover:text-red-400 hover:bg-red-950/20 rounded transition">
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Main OS Body layout */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* Left Drawer Side Navigation tab bar */}
        <nav className="w-52 bg-[#0a0f14] border-r border-slate-900 p-3 shrink-0 flex flex-col gap-1 select-none">
          <span className="text-[9px] font-mono tracking-widest text-slate-600 uppercase pl-3 mb-2 block font-extrabold">
            Navegação
          </span>

          {/* Button tab: Dashboard */}
          <div
            className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-xs font-mono font-medium bg-gradient-to-r from-cyan-950/60 to-[#122330] border-l-2 border-[#00f2fe] text-[#00f2fe]"
          >
            <Home className="w-4 h-4 shrink-0" />
            Home / Painel
          </div>

          <div className="h-[1px] bg-slate-900/80 my-4" />

          {/* Informative credentials status board */}
          <div className="mt-auto p-3.5 rounded-xl bg-slate-950 border border-slate-900 text-[11px] font-mono space-y-2.5">
            <span className="text-[10px] font-bold text-slate-500 block uppercase">
              REQUISITOS / STATUS
            </span>
            <div className="space-y-1.5 text-slate-400 text-[10px]">
              <div className="flex items-center justify-between">
                <span>Pandas:</span>
                <span className="text-emerald-400 font-bold">✔ OK</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Antigravity:</span>
                <span className="text-emerald-400 font-bold">✔ Ativo</span>
              </div>
            </div>
            
            <div className="pt-2 text-center border-t border-slate-900">
              <span className="text-[9px] text-[#00f2fe]/80 bg-cyan-950/30 px-1 py-0.5 rounded font-extrabold uppercase">
                Versão 1.2
              </span>
            </div>
          </div>
        </nav>

        {/* Right Dashboard Client Workspace Container */}
        <main className="flex-1 bg-[#0d131a] overflow-y-auto p-6 md:p-8 space-y-6">
          
          <div className="space-y-6">
            
            {/* Heading Tab */}
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-extrabold tracking-tight text-white mb-1.5">
                  Início Rápido
                </h2>
                <p className="text-slate-400 text-xs font-mono">
                  Gerencie a fila de extração de vídeos e configure o ciclo de migração do robô.
                </p>
              </div>

              <div className="flex items-center gap-2">
                {/* Reset count */}
                <button
                  onClick={handleResetRobot}
                  title="Resetar progresso"
                  className="p-2 border border-slate-800 hover:border-slate-700 bg-[#121921] text-slate-400 hover:text-slate-200 rounded-lg transition duration-200"
                >
                  <RotateCcw className="w-4 h-4" />
                </button>
                
                <div className="text-xs font-mono text-slate-500 bg-slate-950/80 px-3 py-2 border border-slate-900 rounded-lg">
                  Delay Ativo: <span className="text-cyan-400 font-bold">{(delay / 1000).toFixed(1)}s</span>
                </div>
              </div>
            </div>

            {/* Bento Grid layout with 3 active Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-6 items-stretch">
              
              {/* Column 1: NOMES MAPEADOS / SpreadsheetLoader block */}
              <div className="lg:col-span-5 h-full">
                <SpreadsheetLoader
                  rows={rows}
                  onRowsChange={handleRowsChange}
                  columnMapping={columnMapping}
                  onMappingChange={setColumnMapping}
                  onLogAdd={addLog}
                />
              </div>

              {/* Column 2: STACKED COMANDO BUTTONS */}
              <div className="lg:col-span-3 flex flex-col justify-center gap-4">
                {/* PREPARAR ROBÔ BUTTON */}
                <button
                  onClick={handlePrepareRobot}
                  className={`group w-full py-6 px-4 rounded-xl border flex flex-col items-center justify-center gap-3 transition-all duration-300 font-mono text-xs uppercase font-extrabold tracking-widest ${
                    automationState === 'PREPARED' || automationState === 'MIGRATING' || automationState === 'COMPLETED'
                      ? 'bg-slate-900/60 border-slate-800 text-slate-500 cursor-default'
                      : 'bg-cyan-500/10 hover:bg-cyan-500/20 text-[#00f2fe] border-cyan-500/25 hover:shadow-[0_0_15px_rgba(0,242,254,0.15)] cursor-pointer'
                  }`}
                >
                  <Bot className={`w-10 h-10 transition-transform ${automationState === 'IDLE' ? 'group-hover:scale-110 text-[#00f2fe]' : 'text-slate-600'}`} />
                  <span className="text-center">PREPARAR ROBÔ</span>
                </button>

                {/* COMEÇAR AUTOMAÇÃO BUTTON */}
                <button
                  onClick={handleStartAutomation}
                  disabled={rows.length === 0}
                  className={`group w-full py-6 px-4 rounded-xl border flex flex-col items-center justify-center gap-3 transition-all duration-300 font-mono text-xs uppercase font-extrabold tracking-widest cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed ${
                    automationState === 'MIGRATING'
                      ? 'bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 border-amber-500/20'
                      : 'bg-cyan-500/15 hover:bg-cyan-500/25 text-[#00f2fe] border-cyan-500/30 font-bold hover:shadow-[0_0_20px_rgba(0,242,254,0.2)]'
                  }`}
                >
                  {automationState === 'MIGRATING' ? (
                    <Pause className="w-10 h-10 text-amber-400 animate-pulse" />
                  ) : (
                    <Play className="w-10 h-10 text-cyan-400 group-hover:scale-110 transition-transform" />
                  )}
                  <span className="text-center">
                    {automationState === 'MIGRATING' ? 'PAUSAR AUTOMAÇÃO' : 'COMEÇAR AUTOMAÇÃO'}
                  </span>
                </button>
              </div>

              {/* Column 3: RADIAL AND LINEAR PROGRESS CARD */}
              <div className="lg:col-span-4 h-full">
                <StatusCard
                  processed={processedCount}
                  total={rows.length}
                  percent={progressPercent}
                />
              </div>

            </div>

            {/* Console log footer section */}
            <TerminalConsole
              logs={logs}
              automationState={automationState}
              onClearLogs={() => setLogs([])}
              autoScroll={autoScrollLogs}
              onToggleAutoScroll={() => setAutoScrollLogs(!autoScrollLogs)}
            />

          </div>

        </main>
      </div>

    </div>
  );
}
