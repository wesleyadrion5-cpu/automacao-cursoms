import React, { useRef, useState } from 'react';
import { MappedRow } from '../types';
import { FileSpreadsheet, Upload, Download, Eye, Plus, Trash2, Edit3, Check } from 'lucide-react';

interface SpreadsheetLoaderProps {
  rows: MappedRow[];
  onRowsChange: (newRows: MappedRow[]) => void;
  columnMapping: { modulo: string; video: string; duracao: string; extra: string };
  onMappingChange: (mapping: { modulo: string; video: string; duracao: string; extra: string }) => void;
  onLogAdd: (level: 'INFO' | 'SUCCESS' | 'WARNING' | 'ERROR', msg: string) => void;
}

export default function SpreadsheetLoader({
  rows,
  onRowsChange,
  columnMapping,
  onMappingChange,
  onLogAdd,
}: SpreadsheetLoaderProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [showPreview, setShowPreview] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  
  // States for live adding direct row item
  const [newModName, setNewModName] = useState('');
  const [newVidName, setNewVidName] = useState('');
  const [newDuration, setNewDuration] = useState('');
  const [newExtra, setNewExtra] = useState('');

  // Sample data to preload
  const handleLoadSamples = () => {
    const samples: MappedRow[] = [
      { id: '1', modulo: 'Módulo 1: Fundamentos Organizacionais', video: 'Trilha Estratégica - Vídeo 1', duracao: '12:15', extra: 'Link-A101' },
      { id: '2', modulo: 'Módulo 1: Fundamentos Organizacionais', video: 'Satalia - Vídeo 1', duracao: '10:45', extra: 'Link-A102' },
      { id: '3', modulo: 'Módulo 2: Arquitetura Complexa', video: 'Extraindo Vídeo 3/9', duracao: '15:20', extra: 'Link-B201' },
      { id: '4', modulo: 'Módulo 2: Arquitetura Complexa', video: 'Trilha Estratégica - Vídeo 2', duracao: '08:50', extra: 'Link-B202' },
      { id: '5', modulo: 'Módulo 3: Consolidação de Dados', video: 'Integração Final - Vídeo 1', duracao: '18:30', extra: 'Link-C301' },
      { id: '6', modulo: 'Módulo 3: Consolidação de Dados', video: 'Painel Geral - Vídeo 2', duracao: '14:15', extra: 'Link-C302' },
      { id: '7', modulo: 'Módulo 4: Monitoramento Avançado', video: 'Auditória Geral - Vídeo 1', duracao: '09:40', extra: 'Link-D401' },
      { id: '8', modulo: 'Módulo 4: Monitoramento Avançado', video: 'Segurança Operacional - Vídeo 2', duracao: '11:05', extra: 'Link-D402' },
      { id: '9', modulo: 'Módulo 5: Implantação e Release', video: 'Pipeline de Produção - Vídeo 3', duracao: '13:50', extra: 'Link-E501' },
      { id: '10', modulo: 'Módulo 5: Implantação e Release', video: 'Checklist de Entrega - Vídeo 4', duracao: '16:00', extra: 'Link-E502' },
    ];
    onRowsChange(samples);
    onLogAdd('SUCCESS', `Carregado template completo com ${samples.length} registros mapeados.`);
  };

  // Convert current state rows to downloadable CSV script template
  const handleDownloadTemplate = () => {
    const header = `${columnMapping.modulo},${columnMapping.video},${columnMapping.duracao},${columnMapping.extra}`;
    const dataRows = rows.map(
      (r) => `"${r.modulo.replace(/"/g, '""')}","${r.video.replace(/"/g, '""')}","${r.duracao}","${r.extra}"`
    );
    const content = [header, ...dataRows].join('\n');
    const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `planilha_dona_francisca.csv`;
    link.click();
    URL.revokeObjectURL(url);
    onLogAdd('INFO', 'Download de planilha de exemplo concluído!');
  };

  // Drag and drop CSV parser implementation
  const parseCSV = (text: string) => {
    try {
      const lines = text.split(/\r?\n/).filter(line => line.trim() !== '');
      if (lines.length < 2) {
        onLogAdd('ERROR', 'O documento CSV importado precisa ter um cabeçalho e ao menos uma linha de dados.');
        return;
      }

      // Parse headers
      const headers = lines[0].split(',').map(h => h.trim().replace(/^["']|["']$/g, ''));
      
      // Auto-configure column mapping if matches standard headers
      const updatedMapping = { ...columnMapping };
      if (headers[0]) updatedMapping.modulo = headers[0];
      if (headers[1]) updatedMapping.video = headers[1];
      if (headers[2]) updatedMapping.duracao = headers[2];
      if (headers[3]) updatedMapping.extra = headers[3];
      onMappingChange(updatedMapping);

      const parsedRows: MappedRow[] = [];
      for (let i = 1; i < lines.length; i++) {
        // Regex to parse CSV lines safely handling quotation commas
        const matches = lines[i].match(/(".*?"|[^",\s]+)(?=\s*,|\s*$)/g) || lines[i].split(',');
        const cleanValues = matches.map(val => val.trim().replace(/^["']|["']$/g, ''));

        parsedRows.push({
          id: String(i),
          modulo: cleanValues[0] || `Modulo ${i}`,
          video: cleanValues[1] || `Video ${i}`,
          duracao: cleanValues[2] || '10:00',
          extra: cleanValues[3] || 'N/A',
        });
      }

      onRowsChange(parsedRows);
      onLogAdd('SUCCESS', `Planilha customizada carregada! ${parsedRows.length} linhas de processamento configuradas.`);
      setShowPreview(true);
    } catch (err: any) {
      onLogAdd('ERROR', `Falha ao interpretar a tabela: ${err.message}`);
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      if (event.target?.result) {
        parseCSV(event.target.result as string);
      }
    };
    reader.readAsText(file);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        if (event.target?.result) {
          parseCSV(event.target.result as string);
        }
      };
      reader.readAsText(file);
    }
  };

  const handleAddCustomRow = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newModName || !newVidName) {
      alert('Nome do Módulo e Nome do Vídeo são obrigatórios!');
      return;
    }
    const newRow: MappedRow = {
      id: String(Date.now()),
      modulo: newModName,
      video: newVidName,
      duracao: newDuration || '10:00',
      extra: newExtra || 'Link-Manual',
    };
    const updated = [...rows, newRow];
    onRowsChange(updated);
    setNewModName('');
    setNewVidName('');
    setNewDuration('');
    setNewExtra('');
    onLogAdd('INFO', `Item '${newVidName}' adicionado manualmente à fila da automação.`);
  };

  const handleClearRows = () => {
    onRowsChange([]);
    onLogAdd('WARNING', 'Fila de itens de processo limpa.');
  };

  return (
    <div className="bg-[#131b26]/90 backdrop-blur-md border border-slate-800 rounded-xl p-6 shadow-xl flex flex-col justify-between h-full radial-glow">
      <div>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-[#00f0ff]">
              <FileSpreadsheet className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-mono tracking-widest font-semibold uppercase text-slate-400">
                PLANILHA DE FLUXO
              </h2>
              <p className="text-[#00f0ff] font-sans font-bold text-lg leading-tight mt-0.5">
                NOMES MAPEADOS
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            <button
              onClick={handleLoadSamples}
              className="text-[10px] font-mono border border-slate-800 hover:border-slate-700 bg-slate-900/60 hover:bg-slate-900 text-slate-300 py-1.5 px-3 rounded transition-all duration-200"
            >
              Exemplo Padrão
            </button>
            {rows.length > 0 && (
              <button
                onClick={handleClearRows}
                title="Limpar todos os registros"
                className="p-1.5 border border-red-950/20 text-red-400 hover:text-red-300 bg-red-950/10 hover:bg-red-950/20 rounded transition-all duration-200"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>

        <p className="text-slate-400 text-xs leading-relaxed mb-4">
          Carregue uma planilha com colunas informando os módulos e conexões de mídias. O robô irá criar cada estrutura e os módulos automaticamente no novo sistema.
        </p>

        {/* Drag n drop File Box */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-5 mb-4 text-center cursor-pointer transition-all duration-300 flex flex-col justify-center items-center select-none ${
            dragOver
              ? 'border-cyan-400 bg-cyan-950/20'
              : 'border-slate-800 bg-[#0a0f18] hover:border-slate-700 hover:bg-slate-900/50'
          }`}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            accept=".csv, .txt, .xlsx"
            className="hidden"
          />

          <Upload className={`w-8 h-8 mb-2 transition-transform duration-300 ${dragOver ? 'scale-110 text-cyan-400' : 'text-slate-500'}`} />
          
          <span className="text-xs font-mono font-semibold text-slate-200 block mb-1">
            ARRASTE OU CARREGUE CLICANDO AQUI
          </span>
          <span className="text-[10px] font-mono text-slate-500">
            Aceita arquivos .CSV e planilhas formatadas
          </span>

          {rows.length > 0 && (
            <div className="mt-3 px-3 py-1 rounded bg-cyan-950/30 border border-cyan-800/20 inline-flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
              <span className="text-[10px] font-mono text-cyan-200">{rows.length} itens prontos para automação</span>
            </div>
          )}
        </div>


      </div>

      {/* Primary Actions Bottom */}
      <div className="space-y-2 mt-auto">
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={handleDownloadTemplate}
            disabled={rows.length === 0}
            className="flex items-center justify-center gap-1.5 text-[11px] font-mono border border-slate-800 hover:border-slate-700 bg-[#0a0f18] hover:bg-slate-900 text-slate-200 py-2.5 rounded-lg transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Download className="w-3.5 h-3.5" />
            Baixar CSV
          </button>
          
          <button
            onClick={() => setShowPreview(!showPreview)}
            disabled={rows.length === 0}
            className="flex items-center justify-center gap-1.5 text-[11px] font-mono bg-cyan-500/10 hover:bg-cyan-500/20 text-[#00f0ff] border border-cyan-500/20 py-2.5 rounded-lg transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Eye className="w-3.5 h-3.5" />
            {showPreview ? 'Fechar Grade' : 'Ver Grade'}
          </button>
        </div>

        {/* Action Button: MIGRAR - NOMES MAPEADOS */}
        <button
          onClick={() => {
            if (rows.length === 0) {
              handleLoadSamples();
            } else {
              setShowPreview(true);
            }
          }}
          className="w-full flex items-center justify-center gap-2 py-3 bg-[#00f2fe] text-[#0a0f18] hover:bg-[#00d7e6] hover:shadow-[0_0_15px_rgba(0,242,254,0.3)] transition-all duration-300 font-mono text-xs font-bold uppercase rounded-lg"
        >
          <FileSpreadsheet className="w-4 h-4 shrink-0" />
          MIGRAR - NOMES MAPEADOS (PLANILHA)
        </button>

        {/* Spreadsheets Modal Preview Overlaid inside the column layout */}
        {showPreview && rows.length > 0 && (
          <div className="mt-4 border border-slate-800 bg-[#0a0f18] rounded-xl overflow-hidden shadow-xl animate-in fade-in duration-200">
            <div className="flex items-center justify-between px-3 py-2 bg-[#101722] border-b border-slate-800">
              <span className="text-[10px] font-mono font-bold tracking-wider text-slate-300 uppercase">
                Visualizador de Registros ({rows.length} itens)
              </span>
              <button
                onClick={() => setShowPreview(false)}
                className="text-xs hover:text-white text-slate-400 font-bold"
              >
                ✕
              </button>
            </div>

            {/* Micro grid display table */}
            <div className="max-h-56 overflow-y-auto overflow-x-auto text-xs font-mono">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-[#111722]/80 text-[10px] text-slate-500 border-b border-slate-800/80 uppercase">
                    <th className="p-2 pl-3">Item</th>
                    <th className="p-2">{columnMapping.modulo}</th>
                    <th className="p-2">{columnMapping.video}</th>
                    <th className="p-2 text-right pr-3">{columnMapping.duracao}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/40 text-slate-400">
                  {rows.map((row, idx) => (
                    <tr key={row.id} className="hover:bg-slate-900/40 transition-colors">
                      <td className="p-2 pl-3 text-slate-600 font-semibold">{idx + 1}</td>
                      <td className="p-2 text-slate-200 font-medium max-w-[120px] truncate" title={row.modulo}>
                        {row.modulo}
                      </td>
                      <td className="p-2 text-cyan-400/90 max-w-[130px] truncate" title={row.video}>
                        {row.video}
                      </td>
                      <td className="p-2 text-right text-emerald-400 font-medium pr-3">{row.duracao}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Quick Manual Entry Add-On Form inside viewer */}
            <form onSubmit={handleAddCustomRow} className="p-3 bg-[#111722]/50 border-t border-slate-800 grid grid-cols-4 gap-1.5">
              <input
                type="text"
                placeholder="Módulo..."
                value={newModName}
                onChange={(e) => setNewModName(e.target.value)}
                className="bg-[#0b1019] border border-slate-800 rounded px-2 py-1 text-[11px] text-slate-300 hover:border-slate-700"
              />
              <input
                type="text"
                placeholder="Vídeo..."
                value={newVidName}
                onChange={(e) => setNewVidName(e.target.value)}
                className="bg-[#0b1019] border border-slate-800 rounded px-2 py-1 text-[11px] text-slate-300 hover:border-slate-700"
              />
              <input
                type="text"
                placeholder="Duração..."
                value={newDuration}
                onChange={(e) => setNewDuration(e.target.value)}
                className="bg-[#0b1019] border border-slate-800 rounded px-2 py-1 text-[11px] text-slate-300 hover:border-slate-700"
              />
              <button
                type="submit"
                className="bg-[#00f2fe]/10 hover:bg-[#00f2fe]/20 text-[#00f2fe] border border-[#00f2fe]/30 rounded font-bold text-[10px] flex items-center justify-center gap-1 cursor-pointer"
              >
                <Plus className="w-3 h-3" /> Add
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}
