/**
 * Townsquare Interactive Ad Creative Studio - Frontend
 *
 * Created by Jason Akatiff
 * iSCALE.com | A4D.com
 * Telegram: @jasonakatiff
 * Email: jason@jasonakatiff.com
 */

import React, { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { BrandProvider } from './context/BrandContext';
import { CampaignProvider } from './context/CampaignContext';
import { ToastProvider } from './context/ToastContext';
import PrivateRoute from './components/PrivateRoute';
import ErrorBoundary from './components/ErrorBoundary';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
const CreateAds = lazy(() => import('./pages/CreateAds'));
const ImageAds = lazy(() => import('./pages/ImageAds'));
const VideoAds = lazy(() => import('./pages/VideoAds'));
const ModularAds = lazy(() => import('./pages/ModularAds'));
const AdModulesLibrary = lazy(() => import('./pages/AdModulesLibrary'));
const Reporting = lazy(() => import('./pages/Reporting'));
const CustomerProfiles = lazy(() => import('./pages/CustomerProfiles'));
const AIPersonas = lazy(() => import('./pages/AIPersonas'));
const FacebookCampaigns = lazy(() => import('./pages/FacebookCampaigns'));
const WinningAds = lazy(() => import('./pages/WinningAds'));
const GeneratedAds = lazy(() => import('./pages/GeneratedAds'));
const Research = lazy(() => import('./pages/Research'));
const ResearchSettings = lazy(() => import('./pages/ResearchSettings'));
const BrandScrapes = lazy(() => import('./pages/BrandScrapes'));
const AdRemix = lazy(() => import('./pages/AdRemix'));
const Settings = lazy(() => import('./pages/Settings'));
const Login = lazy(() => import('./pages/Login'));
const Register = lazy(() => import('./pages/Register'));
const UserManagement = lazy(() => import('./pages/UserManagement'));

function App() {
  return (
    <ToastProvider>
      <AuthProvider>
        <BrandProvider>
          <CampaignProvider>
            <BrowserRouter>
              <ErrorBoundary>
                <Suspense fallback={<div className="min-h-screen grid place-items-center">Loading...</div>}>
                <Routes>
                  {/* Public routes */}
                  <Route path="/login" element={<Login />} />
                  <Route path="/register" element={<Register />} />

                  {/* Protected routes */}
                  <Route
                    path="/"
                    element={
                      <PrivateRoute>
                        <Layout />
                      </PrivateRoute>
                    }
                  >
                    <Route index element={<Dashboard />} />
                    <Route path="research" element={<Research />} />
                    <Route path="research/brand-scrapes" element={<BrandScrapes />} />
                    <Route path="research/settings" element={<ResearchSettings />} />
                    <Route path="build-creatives" element={<CreateAds />} />
                    <Route path="modular-ads" element={<ModularAds />} />
                    <Route path="ad-modules-library" element={<AdModulesLibrary />} />
                    <Route path="image-ads" element={<ImageAds />} />
                    <Route path="video-ads" element={<VideoAds />} />
                    <Route path="facebook-campaigns" element={<FacebookCampaigns />} />
                    <Route path="winning-ads" element={<WinningAds />} />
                    <Route path="generated-ads" element={<GeneratedAds />} />
                    <Route path="profiles" element={<CustomerProfiles />} />
                    <Route path="personas" element={<AIPersonas />} />
                    <Route path="ad-remix" element={<AdRemix />} />
                    <Route path="reporting" element={<Reporting />} />
                    <Route path="settings" element={<Settings />} />
                    <Route
                      path="users"
                      element={
                        <PrivateRoute requiredRole="admin">
                          <UserManagement />
                        </PrivateRoute>
                      }
                    />
                  </Route>
                </Routes>
                </Suspense>
              </ErrorBoundary>
            </BrowserRouter>
          </CampaignProvider>
        </BrandProvider>
      </AuthProvider>
    </ToastProvider>
  );
}

export default App;
