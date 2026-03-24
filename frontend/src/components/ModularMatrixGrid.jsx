import React from 'react';

export default function ModularMatrixGrid({ scripts }) {
    if (!scripts || scripts.length === 0) return null;

    return (
        <div className="space-y-6">
            {scripts.map((script, i) => (
                <div key={i} className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                    <div className="bg-slate-50 p-4 border-b border-gray-200 flex justify-between items-center">
                        <div>
                            <span className="text-xs font-mono bg-purple-100 text-purple-700 px-2 py-1 rounded">
                                {script.naming_convention_code}
                            </span>
                        </div>
                        <div className="flex gap-2">
                            <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">Hook: {script.intro_format}</span>
                            <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">Bridge: {script.bridge_type}</span>
                        </div>
                    </div>
                    <div className="p-6 grid grid-cols-1 md:grid-cols-4 gap-6">
                        <div className="space-y-2">
                            <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider">0-7s Hook</h4>
                            <p className="text-sm text-gray-900">{script.intro_text}</p>
                        </div>
                        <div className="space-y-2">
                            <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider">7-20s Bridge</h4>
                            <p className="text-sm text-gray-900">{script.bridge_text}</p>
                        </div>
                        <div className="space-y-2">
                            <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider">20-40s Core</h4>
                            <div className="text-xs font-medium text-gray-500 mb-1">{script.core_type}</div>
                            <p className="text-sm text-gray-900">{script.core_text}</p>
                        </div>
                        <div className="space-y-2">
                            <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider">40-50s CTA</h4>
                            <div className="text-xs font-medium text-gray-500 mb-1">{script.cta_type}</div>
                            <p className="text-sm text-gray-900">{script.cta_text}</p>
                        </div>
                    </div>
                </div>
            ))}
        </div>
    );
}
