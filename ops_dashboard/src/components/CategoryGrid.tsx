import React, { useState, useMemo } from 'react';
import { Search, LayoutGrid, Table as TableIcon, Filter } from 'lucide-react';
import { PipelineStatusResponse } from '../types/pipeline';
import { CategoryCard } from './CategoryCard';
import { CATEGORY_CONFIG, formatRelativeTime, formatExactDateTime } from '../utils/formatters';

interface CategoryGridProps {
  telemetry: PipelineStatusResponse | null;
}

export const CategoryGrid: React.FC<CategoryGridProps> = ({ telemetry }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [showActiveOnly, setShowActiveOnly] = useState(false);
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');

  const categoriesList = useMemo(() => {
    if (!telemetry) return [];
    return Object.values(telemetry.categories);
  }, [telemetry]);

  const filteredCategories = useMemo(() => {
    return categoriesList.filter((cat) => {
      if (showActiveOnly && cat.totalFiles === 0) return false;
      if (!searchQuery.trim()) return true;

      const q = searchQuery.toLowerCase();
      const config = CATEGORY_CONFIG[cat.category];
      const matchLabel = config?.label.toLowerCase().includes(q);
      const matchKey = cat.category.toLowerCase().includes(q);
      const matchFile = cat.latestFileName?.toLowerCase().includes(q);

      return matchLabel || matchKey || matchFile;
    });
  }, [categoriesList, showActiveOnly, searchQuery]);

  return (
    <div className="space-y-4">
      {/* Controls Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-slate-900/60 p-3 rounded-xl border border-slate-800/80">
        {/* Search */}
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search categories or latest file names..."
            className="w-full bg-slate-950/80 border border-slate-800 rounded-lg pl-9 pr-4 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500/50 transition-colors"
          />
        </div>

        {/* Filter toggles */}
        <div className="flex items-center gap-2 self-end sm:self-center">
          <button
            onClick={() => setShowActiveOnly(!showActiveOnly)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
              showActiveOnly
                ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30'
                : 'bg-slate-950/60 text-slate-400 border-slate-800 hover:text-slate-200'
            }`}
          >
            <Filter className="w-3.5 h-3.5" />
            <span>Active Only</span>
          </button>

          {/* View mode toggle */}
          <div className="flex items-center bg-slate-950/80 border border-slate-800 rounded-lg p-0.5">
            <button
              onClick={() => setViewMode('grid')}
              title="Grid View"
              className={`p-1.5 rounded ${
                viewMode === 'grid'
                  ? 'bg-slate-800 text-cyan-400'
                  : 'text-slate-500 hover:text-slate-300'
              } transition-colors`}
            >
              <LayoutGrid className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setViewMode('table')}
              title="Table View"
              className={`p-1.5 rounded ${
                viewMode === 'table'
                  ? 'bg-slate-800 text-cyan-400'
                  : 'text-slate-500 hover:text-slate-300'
              } transition-colors`}
            >
              <TableIcon className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Grid or Table Display */}
      {viewMode === 'grid' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filteredCategories.map((cat) => (
            <CategoryCard key={cat.category} telemetry={cat} />
          ))}
          {filteredCategories.length === 0 && (
            <div className="col-span-full text-center py-12 text-slate-500 text-sm">
              No categories match your search criteria.
            </div>
          )}
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/60">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/80 text-slate-400 uppercase font-semibold text-[10px] tracking-wider border-b border-slate-800">
              <tr>
                <th className="px-4 py-3">Category</th>
                <th className="px-4 py-3 text-right">Processed Files</th>
                <th className="px-4 py-3 text-right">Storage</th>
                <th className="px-4 py-3">Latest File Name</th>
                <th className="px-4 py-3">Latest Modified Time</th>
                <th className="px-4 py-3 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {filteredCategories.map((cat) => {
                const config = CATEGORY_CONFIG[cat.category];
                return (
                  <tr
                    key={cat.category}
                    className={`hover:bg-slate-800/40 transition-colors ${
                      cat.isPulsing ? 'bg-cyan-500/10' : ''
                    }`}
                  >
                    <td className="px-4 py-3">
                      <div className="font-semibold text-white flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${config?.accentBg || 'bg-slate-700'}`} />
                        {config?.label || cat.category}
                      </div>
                      <div className="text-[10px] text-slate-500 font-mono">{cat.category}</div>
                    </td>
                    <td className="px-4 py-3 text-right font-mono font-medium">
                      {cat.totalFiles}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-slate-400">
                      {cat.totalSizeFormatted}
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-200 truncate max-w-[280px]">
                      {cat.latestFileName || <span className="text-slate-600 italic">None</span>}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className="cursor-help hover:text-cyan-400 transition-colors"
                        title={formatExactDateTime(cat.latestFileModifiedAt)}
                      >
                        {formatRelativeTime(cat.latestFileModifiedAt)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                          cat.totalFiles > 0
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                            : 'bg-slate-800 text-slate-500'
                        }`}
                      >
                        {cat.totalFiles > 0 ? 'Active' : 'Idle'}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
