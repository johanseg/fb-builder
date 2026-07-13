import { useToast } from '../context/ToastContext';
import React, { useCallback, useEffect, useState } from 'react';
import { ChevronRight, Loader, Building2, CreditCard, TrendingUp, Calendar, DollarSign, AlertCircle, CheckSquare, Square } from 'lucide-react';
import { useCampaign } from '../context/CampaignContext';
import { getAdAccounts } from '../lib/facebookApi';

const AdAccountStep = ({ onNext }) => {
    const { showWarning } = useToast();
    const { selectedAdAccount, setSelectedAdAccount, extraAdAccounts, setExtraAdAccounts } = useCampaign();
    const [adAccounts, setAdAccounts] = useState([]);
    const [loadingAccounts, setLoadingAccounts] = useState(true);
    const [accountsError, setAccountsError] = useState(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [showDropdown, setShowDropdown] = useState(false);

    const fetchAdAccounts = useCallback(async () => {
        setLoadingAccounts(true);
        setAccountsError(null);
        try {
            const accounts = await getAdAccounts();
            setAdAccounts(accounts);

            // Try to restore last selected account from localStorage
            const lastAccountId = localStorage.getItem('lastSelectedAdAccountId');
            if (lastAccountId) {
                const lastAccount = accounts.find(a => a.id === lastAccountId);
                if (lastAccount) {
                    setSelectedAdAccount(lastAccount);
                    setSearchQuery(lastAccount.name);
                } else if (accounts.length > 0) {
                    setSelectedAdAccount(accounts[0]);
                    setSearchQuery(accounts[0].name);
                }
            } else if (accounts.length > 0 && !selectedAdAccount) {
                setSelectedAdAccount(accounts[0]);
                setSearchQuery(accounts[0].name);
            }
        } catch (error) {
            console.error('Error fetching ad accounts:', error);
            setAccountsError(error.message);
        } finally {
            setLoadingAccounts(false);
        }
    }, [selectedAdAccount, setSelectedAdAccount]);

    useEffect(() => {
        fetchAdAccounts();
    }, [fetchAdAccounts]);

    // Filter ad accounts based on search query
    const filteredAccounts = adAccounts.filter(account =>
        account.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        account.accountId.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const handleAccountSelect = (account) => {
        setSelectedAdAccount(account);
        setSearchQuery(account.name);
        setShowDropdown(false);
        // The primary account can't also be an extra
        setExtraAdAccounts(prev => prev.filter(a => a.id !== account.id));
        // Save to localStorage for next time
        if (account) {
            localStorage.setItem('lastSelectedAdAccountId', account.id);
        }
    };

    const toggleExtraAccount = (account) => {
        setExtraAdAccounts(prev =>
            prev.some(a => a.id === account.id)
                ? prev.filter(a => a.id !== account.id)
                : [...prev, account]
        );
    };

    const handleNext = () => {
        if (!selectedAdAccount) {
            showWarning('Please select an ad account');
            return;
        }
        onNext();
    };

    return (
        <div>
            <h2 className="text-2xl font-bold mb-2">Select Ad Account</h2>
            <p className="text-muted-foreground mb-6">
                Choose which Facebook ad account you want to use for this campaign.
            </p>

            <div className="p-4 bg-secondary rounded-lg border border-border">
                <label className="block text-sm font-medium text-foreground mb-2">
                    Ad Account *
                </label>
                {loadingAccounts ? (
                    <div className="flex items-center gap-2 text-muted-foreground">
                        <Loader className="animate-spin" size={16} />
                        <span>Loading ad accounts...</span>
                    </div>
                ) : accountsError ? (
                    <div className="text-red-600 text-sm">
                        Error loading ad accounts: {accountsError}
                        <button
                            onClick={fetchAdAccounts}
                            className="ml-2 text-amber-600 hover:underline"
                        >
                            Retry
                        </button>
                    </div>
                ) : adAccounts.length === 0 ? (
                    <div className="text-muted-foreground text-sm">
                        No ad accounts found. Please check your access token.
                    </div>
                ) : (
                    <div className="relative">
                        <input
                            type="text"
                            value={searchQuery}
                            onChange={(e) => {
                                setSearchQuery(e.target.value);
                                setShowDropdown(true);
                            }}
                            onFocus={() => {
                                setShowDropdown(true);
                                if (selectedAdAccount && searchQuery === selectedAdAccount.name) {
                                    setSearchQuery('');
                                }
                            }}
                            placeholder="Search ad accounts by name or ID..."
                            className="w-full px-4 py-2 border border-border rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                        />

                        {showDropdown && filteredAccounts.length > 0 && (
                            <div className="absolute z-10 w-full mt-1 bg-card border border-border rounded-lg shadow-lg max-h-60 overflow-y-auto">
                                {filteredAccounts.map(account => (
                                    <div
                                        key={account.id}
                                        onClick={() => handleAccountSelect(account)}
                                        className={`px-4 py-3 cursor-pointer hover:bg-amber-50 border-b border-border last:border-b-0 ${selectedAdAccount?.id === account.id ? 'bg-amber-50' : ''
                                            }`}
                                    >
                                        <div className="font-medium text-foreground">{account.name}</div>
                                        <div className="text-sm text-muted-foreground">
                                            ID: {account.accountId} • {account.currency} • {account.status === 1 ? 'Active' : 'Inactive'}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}

                        {showDropdown && searchQuery && filteredAccounts.length === 0 && (
                            <div className="absolute z-10 w-full mt-1 bg-card border border-border rounded-lg shadow-lg p-4 text-muted-foreground text-sm">
                                No accounts match "{searchQuery}"
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Account Details Card */}
            {selectedAdAccount && !showDropdown && (
                <div className="mt-6 bg-card border border-border rounded-lg shadow-sm overflow-hidden">
                    {/* Header */}
                    <div className="bg-gradient-to-r from-amber-100 to-orange-100 p-4 border-b border-amber-200">
                        <h3 className="text-lg font-bold text-foreground">{selectedAdAccount.name}</h3>
                        <div className="flex items-center gap-4 mt-2 text-amber-700 text-sm">
                            <span>ID: {selectedAdAccount.accountId}</span>
                            <span>•</span>
                            <span className={`px-2 py-0.5 rounded text-xs font-medium ${selectedAdAccount.status === 1 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                                }`}>
                                {selectedAdAccount.status === 1 ? 'Active' : 'Inactive'}
                            </span>
                        </div>
                    </div>

                    {/* Account Details Grid */}
                    <div className="grid grid-cols-2 gap-4 p-4">
                        {/* Currency & Timezone */}
                        <div className="flex items-start gap-3">
                            <DollarSign className="text-muted-foreground mt-0.5" size={18} />
                            <div>
                                <div className="text-xs text-muted-foreground font-medium">Currency</div>
                                <div className="text-sm text-foreground">{selectedAdAccount.currency}</div>
                            </div>
                        </div>

                        <div className="flex items-start gap-3">
                            <Calendar className="text-muted-foreground mt-0.5" size={18} />
                            <div>
                                <div className="text-xs text-muted-foreground font-medium">Timezone</div>
                                <div className="text-sm text-foreground">{selectedAdAccount.timezone}</div>
                            </div>
                        </div>

                        {/* Business Name - only if exists */}
                        {selectedAdAccount.businessName && (
                            <div className="col-span-2 flex items-start gap-3">
                                <Building2 className="text-muted-foreground mt-0.5" size={18} />
                                <div>
                                    <div className="text-xs text-muted-foreground font-medium">Business</div>
                                    <div className="text-sm text-foreground">{selectedAdAccount.businessName}</div>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Multi-account launch: replicate into additional accounts */}
            {selectedAdAccount && !showDropdown && adAccounts.length > 1 && (
                <div className="mt-6 bg-card border border-border rounded-lg shadow-sm p-4">
                    <h3 className="text-sm font-semibold text-foreground mb-1">
                        Also launch to other accounts (optional)
                    </h3>
                    <p className="text-xs text-muted-foreground mb-3">
                        The campaign, ad set and ads will be replicated into each selected account.
                        Pages and pixels are loaded from the primary account — make sure the other
                        accounts can use them.
                    </p>
                    <div className="max-h-48 overflow-y-auto space-y-1">
                        {adAccounts.filter(a => a.id !== selectedAdAccount.id).map(account => {
                            const isChecked = extraAdAccounts.some(a => a.id === account.id);
                            return (
                                <button
                                    key={account.id}
                                    type="button"
                                    onClick={() => toggleExtraAccount(account)}
                                    className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left hover:bg-amber-50 ${isChecked ? 'bg-amber-50' : ''}`}
                                >
                                    {isChecked
                                        ? <CheckSquare className="text-amber-600 shrink-0" size={18} />
                                        : <Square className="text-muted-foreground shrink-0" size={18} />}
                                    <span className="text-sm text-foreground truncate">{account.name}</span>
                                    <span className="text-xs text-muted-foreground ml-auto shrink-0">{account.accountId}</span>
                                </button>
                            );
                        })}
                    </div>
                    {extraAdAccounts.length > 0 && (
                        <p className="text-xs text-amber-700 mt-3 font-medium">
                            Launching to {extraAdAccounts.length + 1} accounts total
                        </p>
                    )}
                </div>
            )}

            {/* Navigation */}
            <div className="mt-8 flex justify-end">
                <button
                    onClick={handleNext}
                    disabled={!selectedAdAccount}
                    className="flex items-center gap-2 px-6 py-3 bg-amber-600 text-white rounded-lg font-medium hover:bg-amber-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
                >
                    Next Step <ChevronRight size={20} />
                </button>
            </div>
        </div>
    );
};

export default AdAccountStep;
