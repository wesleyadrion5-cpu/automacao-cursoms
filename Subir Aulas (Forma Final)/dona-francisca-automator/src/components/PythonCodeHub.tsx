import React, { useState } from 'react';
import { generatePythonScript } from '../utils/pythonGenerator';
import { Terminal, Copy, Download, Code, PlayCircle, Settings, Check, HelpCircle } from 'lucide-react';

interface PythonCodeHubProps {
  columnMapping: { modulo: string; video: string; duracao: string; extra: string };
  defaultRobotName: string;
}

export default function PythonCodeHub({ columnMapping, defaultRobotName }: PythonCodeHubProps) {
  const [robotName, setRobotName] = useState(defaultRobotName);
  const [delay, setDelay] = useState(1500); // 1.5 seconds default
  const [copied, setCopied] = useState(false);

  const pythonScript = generatePythonScript(robotName, columnMapping, delay, true);

  const copyToClipboard = () => {
    navigator.clipboard.writeText(pythonScript);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const downloadScriptFile = () => {
    const blob = new Blob([pythonScript], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `automacao_mapeamento.py`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="bg-[#121924] border border-slate-800 rounded-xl p-6 shadow-xl space-y-6 flex flex-col h-full radial-glow">
      {/* Header Info */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-yellow-500/10 border border-yellow-500/20 text-yellow-400">
            <Code className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-mono tracking-widest font-semibold uppercase text-slate-400">
              HUB DE INTEGRAÇÃO PYTHON
            </h2>
            <p className="text-[#00f0ff] font-sans font-bold text-lg leading-tight mt-0.5">
              ROBÔ DE PRODUÇÃO (CÓDIGO FONTE)
            </p>
          </div>
        </div>

        {/* Action button copy and download */}
        <div className="flex items-center gap-2">
          <button
            onClick={copyToClipboard}
            className={`flex items-center justify-center gap-1.5 text-xs font-mono py-2 px-3.5 rounded-lg border transition-all duration-300 font-bold ${
              copied
                ? 'bg-green-500/10 text-green-400 border-green-500/30'
                : 'bg-slate-900 border-slate-800 hover:border-slate-700 text-slate-300'
            }`}
          >
            {copied ? <Check className="w-3.5 h-3.5 animate-bounce" /> : <Copy className="w-3.5 h-3.5" />}
            {copied ? 'Copiado!' : 'Copiar Código'}
          </button>
          
          <button
            onClick={downloadScriptFile}
            className="flex items-center justify-center gap-1.5 text-xs font-mono py-2 px-3.5 rounded-lg bg-[#00f2fe] text-[#0a0f18] hover:bg-[#00d7e6] font-bold transition-all duration-300 hover:shadow-[0_0_12px_rgba(0,242,254,0.3)]"
          >
            <Download className="w-3.5 h-3.5" />
            Baixar .py
          </button>
        </div>
      </div>

      {/* Grid: Left Column parameters, Right Column Code Viewer */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch flex-1">
        {/* Left column settings */}
        <div className="lg:col-span-4 bg-[#0a0f18] border border-slate-800/80 p-5 rounded-xl flex flex-col justify-between space-y-4">
          <div className="space-y-4">
            <div className="flex items-center gap-2 font-mono text-xs text-slate-300 font-semibold uppercase tracking-wider pb-2 border-b border-slate-800/60">
              <Settings className="w-3.5 h-3.5 text-cyan-400" />
              Parâmetros do Script
            </div>

            {/* Variable parameter 1: Robot Name */}
            <div className="space-y-1">
              <label className="text-[11px] font-mono text-slate-400">Identificação do Robô (Nome)</label>
              <input
                type="text"
                value={robotName}
                onChange={(e) => setRobotName(e.target.value)}
                placeholder="Ex. Robô 1"
                className="w-full bg-[#111722] border border-slate-800 rounded px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500 transition-colors"
              />
            </div>

            {/* Variable parameter 2: Delay */}
            <div className="space-y-1">
              <div className="flex justify-between items-center text-[11px] font-mono">
                <span className="text-slate-400">Tempo de Espera (Delay)</span>
                <span className="text-cyan-400 font-bold">{(delay / 1000).toFixed(1)}s</span>
              </div>
              <input
                type="range"
                min="300"
                max="5000"
                step="100"
                value={delay}
                onChange={(e) => setDelay(Number(e.target.value))}
                className="w-full accent-cyan-400 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
              />
              <span className="text-[9px] text-slate-500 font-mono block">Controla os intervalos do sleep() para evitar detecções.</span>
            </div>

            {/* Integration info box */}
            <div className="p-3 bg-yellow-500/5 border border-yellow-500/10 rounded-lg space-y-1.5 text-xs text-slate-300">
              <span className="font-bold text-yellow-400 flex items-center gap-1">
                <HelpCircle className="w-3.5 h-3.5" /> Como rodar no Antigravity:
              </span>
              <p className="text-[10px] leading-relaxed font-mono">
                1. Salve o arquivo como <code className="text-slate-100 bg-slate-900 px-1 rounded">f_automacao.py</code> no diretório do projeto Antigravity.
              </p>
              <p className="text-[10px] leading-relaxed font-mono">
                2. Execute o comando de instalação: 
                <code className="text-cyan-300 block bg-slate-900/85 p-1 mt-1 rounded text-center select-all">pip install pandas</code>
              </p>
              <p className="text-[10px] leading-relaxed font-mono">
                3. Certifique-se de que o arquivo <code className="text-slate-100">planilha_mapeada.csv</code> ou gerado esteja no mesmo diretório.
              </p>
            </div>
          </div>

          <div className="text-[10px] font-mono text-slate-500 flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse shrink-0" />
            O código gerado se adapta dinamicamente às colunas mapeadas.
          </div>
        </div>

        {/* Right column: Interactive Code block */}
        <div className="lg:col-span-8 flex flex-col border border-slate-800 rounded-xl overflow-hidden shadow-inner h-[380px] lg:h-auto">
          {/* Header toolbar */}
          <div className="bg-[#111722] border-b border-slate-800/80 px-4 py-2 flex items-center justify-between">
            <span className="text-[10px] font-mono text-slate-500">FORMATO: PYTHON 3.x • PANDAS</span>
            <div className="flex space-x-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-red-500/30" />
              <span className="w-2.5 h-2.5 rounded-full bg-yellow-500/30" />
              <span className="w-2.5 h-2.5 rounded-full bg-green-500/30" />
            </div>
          </div>

          {/* Interactive view container */}
          <pre className="flex-1 overflow-auto bg-[#0a0f18] p-4 font-mono text-xs text-indigo-200 leading-normal select-text">
            <code>
              {pythonScript.split('\n').map((line, idx) => {
                let color = 'text-slate-300';
                if (line.trim().startsWith('#')) color = 'text-slate-500 italic';
                else if (line.trim().startsWith('def ') || line.trim().startsWith('import ')) color = 'text-[#00f2fe] font-bold';
                else if (line.includes('log(') || line.includes('print(')) color = 'text-teal-400';
                else if (line.includes('time.sleep')) color = 'text-amber-400';

                return (
                  <div key={idx} className="flex">
                    <span className="text-slate-700 w-8 pr-2 select-none text-right border-r border-slate-900">{idx + 1}</span>
                    <span className={`pl-3 ${color}`}>{line}</span>
                  </div>
                );
              })}
            </code>
          </pre>
        </div>
      </div>
    </div>
  );
}
