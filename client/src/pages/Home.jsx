import { useNavigate } from 'react-router-dom';
import heroImg from '../assets/hero.png';
import {
  Satellite,
  Brain,
  TrendingUp,
  Droplets,
  ArrowRight,
  CheckCircle2,
  Leaf,
  Sprout,
} from 'lucide-react';

export const Home = () => {
  const navigate = useNavigate();

  const features = [
    {
      id: 1,
      title: 'Satellite-Based Crop Monitoring',
      description:
        'Continuous high-resolution satellite telemetry tracking vegetation health index (NDVI), canopy density, and field performance in real-time from orbit.',
      icon: Satellite,
    },
    {
      id: 2,
      title: 'AI Crop Type Identification',
      description:
        'Advanced deep neural vision models that automatically classify crop species, map precise field parcel boundaries, and analyze historical crop rotation.',
      icon: Brain,
    },
    {
      id: 3,
      title: 'Growth Stage Estimation',
      description:
        'Phenological growth tracking algorithms predicting plant emergence, vegetative milestones, flowering windows, and optimal harvest timelines.',
      icon: TrendingUp,
    },
    {
      id: 4,
      title: 'Water Stress Detection',
      description:
        'Thermal infrared and multispectral NIR analysis detecting root-zone moisture deficits early, triggering automated precision irrigation recommendations.',
      icon: Droplets,
    },
  ];

  const stats = [
    { number: '25K+', label: 'Happy Farmers' },
    { number: '1.2M+', label: 'Acres Monitored' },
    { number: '30%', label: 'Average Yield Increase' },
    { number: '40%', label: 'Water Saved' },
  ];

  return (
    <div className="space-y-20 pb-16">
      {/* SECTION 1: HERO BANNER (FULL WIDTH hero.png IMAGE WITH SOFTER OFF-WHITE OPACITY) */}
      <section className="relative w-full overflow-hidden bg-[#F9FAF7] min-h-[560px] sm:min-h-[620px] lg:min-h-[680px] flex items-center shadow-xs">
        
        {/* Full Section Width Background Image: hero.png */}
        <div className="absolute inset-0 w-full h-full overflow-hidden">
          <img
            src={heroImg}
            alt="CropSense AI Agriculture Banner"
            className="w-full h-full object-cover object-right lg:object-center"
          />
          {/* Reduced Intensity Off-White Gradient Opacity Overlay */}
          <div className="absolute inset-0 bg-gradient-to-r from-[#F9FAF7]/85 via-[#F9FAF7]/55 via-45% to-transparent" />
        </div>

        {/* Content Aligned Within Container */}
        <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 w-full py-12">
          
          {/* Left Text Block */}
          <div className="max-w-2xl space-y-6 text-left">
            {/* Header Pill Badge */}
            <div className="inline-flex items-center space-x-2 bg-[#EBF4EE]/90 backdrop-blur-xs border border-emerald-900/15 text-[#18392B] px-4 py-1.5 rounded-full text-xs font-bold tracking-wide shadow-xs">
              <Sprout className="w-4 h-4 text-emerald-700" />
              <span>Smart Farming for a Sustainable Future</span>
            </div>

            {/* Main Headline */}
            <h1 className="font-heading font-extrabold text-5xl sm:text-6xl lg:text-7xl leading-[1.1] tracking-tight">
              <span className="text-[#18392B] block">Empowering</span>
              <span className="text-[#18392B] block">Farmers.</span>
              <span className="text-[#00A859] block">Growing</span>
              <span className="text-[#00A859] block">Tomorrow.</span>
            </h1>

            {/* Subtitle Paragraph */}
            <p className="text-slate-700 text-sm sm:text-base lg:text-lg leading-relaxed max-w-xl font-semibold drop-shadow-2xs">
              CropSense AI brings technology, insights, and expertise to help you increase yield, reduce costs, and build a sustainable future.
            </p>

            {/* Action Buttons */}
            <div className="flex flex-wrap items-center gap-4 pt-2">
              <button
                onClick={() => navigate('/fields')}
                className="bg-[#18392B] hover:bg-[#10281E] text-white px-8 py-3.5 rounded-full font-extrabold text-sm transition-all shadow-lg hover:shadow-emerald-900/20 flex items-center space-x-2.5 cursor-pointer group"
              >
                <span>Get Started</span>
                <ArrowRight className="w-4 h-4 text-emerald-300 group-hover:translate-x-1 transition-transform" />
              </button>

              <button
                onClick={() => {
                  const el = document.getElementById('solutions-section');
                  el?.scrollIntoView({ behavior: 'smooth' });
                }}
                className="bg-white/90 hover:bg-white border-2 border-[#18392B] text-[#18392B] font-bold px-7 py-3.5 rounded-full text-sm transition-all shadow-xs flex items-center space-x-2 cursor-pointer"
              >
                <span>Explore Solutions</span>
                <Leaf className="w-4 h-4 text-emerald-700" />
              </button>
            </div>
          </div>

        </div>
      </section>

      {/* SECTION 2: WHAT WE OFFER / 4 SPECIFIED FEATURES GRID */}
      <section id="solutions-section" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center pt-6">
        {/* Section Header */}
        <div className="max-w-3xl mx-auto space-y-3 mb-12">
          <div className="inline-flex items-center space-x-1.5 text-xs font-extrabold uppercase tracking-widest text-emerald-800 bg-[#EBF4EE] border border-emerald-900/10 px-3.5 py-1 rounded-full">
            <Leaf className="w-3.5 h-3.5" />
            <span>WHAT WE OFFER</span>
          </div>
          <h2 className="font-heading font-extrabold text-3xl sm:text-4xl text-[#18392B]">
            Smart Solutions for Modern Farming
          </h2>
          <p className="text-slate-600 text-sm sm:text-base">
            Everything you need to manage your farm efficiently and profitably.
          </p>
        </div>

        {/* 4 Specified Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 text-left">
          {features.map((feature) => {
            const IconComp = feature.icon;
            return (
              <div
                key={feature.id}
                className="bg-white rounded-3xl p-7 border border-slate-200/80 shadow-xs hover:shadow-xl hover:-translate-y-1 transition-all duration-300 flex flex-col justify-between group"
              >
                <div>
                  {/* Icon Circle */}
                  <div className="w-14 h-14 rounded-2xl bg-[#EBF4EE] group-hover:bg-[#18392B] flex items-center justify-center text-[#18392B] group-hover:text-emerald-300 transition-colors mb-6 shadow-xs">
                    <IconComp className="w-7 h-7 stroke-[1.8]" />
                  </div>

                  {/* Title */}
                  <h3 className="font-bold text-lg text-slate-900 mb-3 group-hover:text-[#18392B] transition-colors leading-snug">
                    {feature.title}
                  </h3>

                  {/* Description */}
                  <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
                    {feature.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>

        {/* Explore All Solutions Link */}
        <div className="mt-12">
          <button
            onClick={() => navigate('/dashboard')}
            className="inline-flex items-center space-x-2 text-sm font-bold text-[#18392B] hover:text-emerald-700 transition-colors cursor-pointer group"
          >
            <span>Explore All Solutions</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </button>
        </div>
      </section>

      {/* SECTION 3: DARK GREEN STATS BAR BANNER */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-[#18392B] text-white rounded-3xl p-8 sm:p-12 shadow-xl border border-emerald-900/40">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center divide-y md:divide-y-0 md:divide-x divide-emerald-800/60">
            {stats.map((stat, index) => (
              <div key={index} className={`pt-4 md:pt-0 ${index !== 0 ? 'md:pl-6' : ''}`}>
                <p className="font-heading font-extrabold text-3xl sm:text-4xl lg:text-5xl text-emerald-300 tracking-tight">
                  {stat.number}
                </p>
                <p className="text-xs sm:text-sm text-slate-300 font-medium mt-2">
                  {stat.label}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* SECTION 4: TECHNOLOGY SHOWCASE ("SMART. SIMPLE. POWERFUL.") */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          
          {/* Left Column Text */}
          <div className="lg:col-span-5 space-y-6">
            <div className="inline-flex items-center space-x-1.5 text-xs font-extrabold uppercase tracking-widest text-emerald-800 bg-[#EBF4EE] border border-emerald-900/10 px-3.5 py-1 rounded-full">
              <Leaf className="w-3.5 h-3.5" />
              <span>SMART. SIMPLE. POWERFUL.</span>
            </div>

            <h2 className="font-heading font-extrabold text-3xl sm:text-4xl text-[#18392B] leading-tight">
              Technology that grows with you
            </h2>

            <p className="text-slate-600 text-sm sm:text-base leading-relaxed">
              CropSense AI is your digital farming partner. Access real-time satellite telemetry data, expert recommendations, and smart tools - all in one place.
            </p>

            {/* Checklist */}
            <div className="space-y-3.5 pt-2">
              <div className="flex items-center space-x-3 text-slate-800 font-semibold text-sm">
                <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                <span>Real-time field monitoring</span>
              </div>
              <div className="flex items-center space-x-3 text-slate-800 font-semibold text-sm">
                <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                <span>AI-powered recommendations</span>
              </div>
              <div className="flex items-center space-x-3 text-slate-800 font-semibold text-sm">
                <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                <span>Easy to use on mobile & web</span>
              </div>
            </div>

            <div className="pt-4">
              <button
                onClick={() => navigate('/water-stress')}
                className="bg-[#18392B] hover:bg-[#10281E] text-white px-7 py-3.5 rounded-full font-bold text-sm transition-all shadow-md flex items-center space-x-2 cursor-pointer group"
              >
                <span>Learn More</span>
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </button>
            </div>
          </div>

          {/* Right Column App Showcase UI */}
          <div className="lg:col-span-7 relative">
            <div className="bg-gradient-to-br from-slate-100 to-emerald-50/50 rounded-3xl p-6 sm:p-8 border border-slate-200/80 shadow-lg flex flex-col sm:flex-row items-center gap-6 overflow-hidden">
              
              {/* Smartphone Mockup */}
              <div className="w-full sm:w-56 bg-slate-900 rounded-[32px] p-3 shadow-2xl border-4 border-slate-800 shrink-0 transform -rotate-1 hover:rotate-0 transition-transform">
                <div className="bg-slate-50 rounded-[24px] p-4 text-xs space-y-4">
                  {/* Header */}
                  <div className="flex justify-between items-center pb-2 border-b border-slate-200">
                    <div>
                      <p className="text-[10px] text-slate-400">Hello, Farmer 👋</p>
                      <p className="font-bold text-slate-800">Field Summary</p>
                    </div>
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                  </div>

                  {/* Crop Health Card */}
                  <div className="bg-white p-3 rounded-xl border border-slate-100 shadow-xs space-y-1">
                    <div className="flex justify-between text-[11px] font-semibold text-slate-600">
                      <span>Crop Health</span>
                      <span className="text-emerald-600 font-bold">78%</span>
                    </div>
                    <div className="w-full bg-slate-100 rounded-full h-1.5">
                      <div className="bg-emerald-500 h-1.5 rounded-full w-[78%]"></div>
                    </div>
                  </div>

                  {/* Soil Moisture */}
                  <div className="bg-white p-3 rounded-xl border border-slate-100 shadow-xs space-y-1">
                    <div className="flex justify-between text-[11px] font-semibold text-slate-600">
                      <span>Soil Moisture</span>
                      <span className="text-sky-600 font-bold">65%</span>
                    </div>
                    <div className="w-full bg-slate-100 rounded-full h-1.5">
                      <div className="bg-sky-500 h-1.5 rounded-full w-[65%]"></div>
                    </div>
                  </div>

                  {/* Quick Activity */}
                  <div className="bg-[#18392B] text-white p-3 rounded-xl shadow-xs space-y-1">
                    <p className="text-[10px] text-emerald-300 font-semibold">Upcoming Task</p>
                    <p className="font-bold text-white text-[11px]">Irrigation Scheduled</p>
                    <p className="text-[9px] text-emerald-200">Tonight at 8:00 PM</p>
                  </div>
                </div>
              </div>

              {/* Desktop Dashboard Card Preview */}
              <div className="flex-1 bg-white rounded-2xl p-5 border border-slate-200 shadow-md space-y-4 w-full">
                <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                  <h4 className="font-bold text-slate-900 text-sm">Farm Overview</h4>
                  <span className="text-[11px] font-bold text-emerald-800 bg-emerald-100 px-2.5 py-0.5 rounded-full">
                    Live Satellite
                  </span>
                </div>

                <div className="space-y-2.5">
                  <div className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                    <div className="flex items-center space-x-2.5">
                      <div className="w-8 h-8 rounded-lg bg-emerald-100 text-[#18392B] flex items-center justify-center font-bold text-xs">
                        FA
                      </div>
                      <div>
                        <p className="font-bold text-slate-800 text-xs">Field A - Wheat</p>
                        <p className="text-[10px] text-slate-500">12.5 Acres</p>
                      </div>
                    </div>
                    <span className="text-xs font-bold text-emerald-600">Optimal</span>
                  </div>

                  <div className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                    <div className="flex items-center space-x-2.5">
                      <div className="w-8 h-8 rounded-lg bg-amber-100 text-amber-800 flex items-center justify-center font-bold text-xs">
                        FB
                      </div>
                      <div>
                        <p className="font-bold text-slate-800 text-xs">Field B - Corn</p>
                        <p className="text-[10px] text-slate-500">8.3 Acres</p>
                      </div>
                    </div>
                    <span className="text-xs font-bold text-amber-600">Mild Stress</span>
                  </div>
                </div>

                <div className="pt-2">
                  <button
                    onClick={() => navigate('/dashboard')}
                    className="w-full py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-bold transition-all text-center"
                  >
                    View Analytics Dashboard
                  </button>
                </div>
              </div>

            </div>
          </div>
        </div>
      </section>

      {/* SECTION 5: FOOTER CALLOUT BANNER */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-[#EDF4EE] rounded-3xl p-6 sm:p-10 border border-emerald-900/10 flex flex-col md:flex-row items-center justify-between gap-6 shadow-sm">
          
          {/* Left Text */}
          <div className="flex items-center space-x-4">
            <div className="w-12 h-12 rounded-2xl bg-[#18392B] text-emerald-300 flex items-center justify-center shrink-0 shadow-xs">
              <Leaf className="w-6 h-6" />
            </div>
            <div>
              <p className="font-heading font-bold text-lg sm:text-xl text-[#18392B]">
                Together, let's build a greener and more prosperous tomorrow.
              </p>
              <p className="text-xs sm:text-sm text-slate-600 mt-0.5">
                Join thousands of precision farmers leveraging CropSense AI satellite telemetry today.
              </p>
            </div>
          </div>

          {/* Right Button */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/fields')}
              className="bg-[#18392B] hover:bg-[#10281E] text-white px-6 py-3 rounded-full font-extrabold text-sm transition-all shadow-md flex items-center space-x-2 cursor-pointer"
            >
              <span>Join CropSense AI</span>
              <Leaf className="w-4 h-4 text-emerald-300" />
            </button>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 border-t border-slate-200/80">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500">
          <div className="flex items-center space-x-2">
            <Sprout className="w-4 h-4 text-[#18392B]" />
            <span className="font-bold text-slate-800">CropSense AI</span>
            <span>© {new Date().getFullYear()} All rights reserved. Precision Agriculture Platform.</span>
          </div>

          <div className="flex items-center space-x-6 font-semibold">
            <button onClick={() => navigate('/')} className="hover:text-[#18392B] transition-colors">Home</button>
            <button onClick={() => navigate('/fields')} className="hover:text-[#18392B] transition-colors">My Field</button>
            <button onClick={() => navigate('/dashboard')} className="hover:text-[#18392B] transition-colors">Analytics</button>
            <button onClick={() => navigate('/water-stress')} className="hover:text-[#18392B] transition-colors">Water Stress</button>
          </div>
        </div>
      </footer>
    </div>
  );
};
