import React from 'react';
import { Layers, Activity, RotateCcw } from 'lucide-react';

interface StatusCardProps {
  processed: number;
  total: number;
  percent: number;
}

export default function StatusCard({ processed, total, percent }: StatusCardProps) {
  // SVG stroke math for radial circle (radius=54, circumference=2*pi*54 = 339.29)
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const strokeOffset = circumference - (percent / 100) * circumference;

  return (
    <div id="status-card" className="bg-[#131b26]/80 backdrop-blur-md border border-slate-800 rounded-xl p-6 shadow-xl flex flex-col justify-between h-full select-none">
      <div>
        <h3 className="text-slate-400 text-xs font-mono tracking-widest font-semibold uppercase mb-4 text-center">
          Status da Operação
        </h3>

        {/* Circular Progress Gauge */}
        <div className="flex flex-col items-center justify-center py-4">
          <div className="relative w-40 h-40">
            {/* SVG Progress Circle */}
            <svg className="w-full h-full transform -rotate-90">
              {/* Background trace circle */}
              <circle
                cx="80"
                cy="80"
                r={radius}
                className="stroke-[#1d293b]"
                strokeWidth="10"
                fill="transparent"
              />
              {/* Foreground animated progress bar */}
              <circle
                cx="80"
                cy="80"
                r={radius}
                className="stroke-[#00f0ff] transition-all duration-500 ease-out"
                strokeWidth="10"
                fill="transparent"
                strokeDasharray={circumference}
                strokeDashoffset={strokeOffset}
                strokeLinecap="round"
              />
            </svg>

            {/* Inner Percentage Readout */}
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-4xl font-sans tracking-tight font-extrabold text-white">
                {percent}%
              </span>
              <span className="text-[10px] font-mono tracking-widest text-[#00f0ff] uppercase mt-0.5">
                Mapeamento
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Progress Bars and Count Details */}
      <div className="space-y-4 border-t border-slate-800/60 pt-4">
        <div>
          <div className="flex justify-between items-center mb-1.5 text-xs font-mono">
            <span className="text-slate-400">Módulos Processados</span>
            <span className="text-slate-200 font-bold">{processed} / {total}</span>
          </div>

          {/* Progress fill track */}
          <div className="w-full bg-slate-900 h-2.5 rounded-full overflow-hidden border border-slate-800">
            <div
              className="bg-cyan-500 h-full rounded-full transition-all duration-500 ease-out shadow-[0_0_8px_rgba(6,182,212,0.5)]"
              style={{ width: `${total > 0 ? (processed / total) * 100 : 0}%` }}
            />
          </div>
        </div>

        {/* Minor metrics */}
        <div className="grid grid-cols-2 gap-2 text-[11px] font-mono p-2 bg-[#0a0f18] rounded-lg border border-slate-800/50">
          <div className="flex flex-col items-center justify-center p-1 border-r border-slate-800/80">
            <span className="text-slate-500">Filas de Mídia</span>
            <span className="text-[#00f0ff] font-bold mt-0.5">{total - processed} pendente(s)</span>
          </div>
          <div className="flex flex-col items-center justify-center p-1">
            <span className="text-slate-500">Tipo de Saída</span>
            <span className="text-green-400 font-bold mt-0.5">Mapeado</span>
          </div>
        </div>
      </div>
    </div>
  );
}
