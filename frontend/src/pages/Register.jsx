import React from 'react';
import { Link } from 'react-router-dom';
import { Lock, Shield, UserPlus } from 'lucide-react';

const Register = () => {
    return (
        <div className="min-h-screen bg-gray-900 flex items-center justify-center px-4">
            <div className="max-w-md w-full">
                <div className="bg-gray-800 rounded-lg shadow-xl p-8">
                    <div className="text-center mb-8">
                        <div className="inline-flex items-center justify-center w-16 h-16 bg-green-600 rounded-full mb-4">
                            <UserPlus className="w-8 h-8 text-white" />
                        </div>
                        <h1 className="text-2xl font-bold text-white">Account Access</h1>
                        <p className="text-muted-foreground mt-2">User accounts are provisioned by an administrator.</p>
                    </div>

                    <div className="space-y-4">
                        <div className="rounded-lg border border-gray-700 bg-gray-900/60 p-4 text-left">
                            <div className="mb-3 flex items-center gap-3 text-white">
                                <Shield className="h-5 w-5 text-green-400" />
                                <span className="font-medium">Registration is restricted</span>
                            </div>
                            <p className="text-sm text-gray-300">
                                This app does not allow public self-signup. Ask a workspace administrator to create your account from the user management screen.
                            </p>
                        </div>

                        <div className="rounded-lg border border-gray-700 bg-gray-900/60 p-4 text-left">
                            <div className="mb-3 flex items-center gap-3 text-white">
                                <Lock className="h-5 w-5 text-blue-400" />
                                <span className="font-medium">Already have credentials?</span>
                            </div>
                            <p className="text-sm text-gray-300">
                                Use the sign-in page with the email and password assigned to you.
                            </p>
                        </div>
                    </div>

                    <div className="mt-6 text-center">
                        <p className="text-muted-foreground mb-4">
                            Need access? Contact your Townsquare administrator.
                        </p>
                        <p className="text-muted-foreground">
                            <Link to="/login" className="text-green-500 hover:text-green-400 font-medium">
                                Back to sign in
                            </Link>
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Register;
