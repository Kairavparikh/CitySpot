"use client";
import React, { useState } from "react";
import { Sidebar, SidebarBody, SidebarLink } from "@/components/ui/sidebar";
import { Map, BarChart3, MessageSquare, Settings, MapPin } from "lucide-react";
import Link from "next/link";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

export default function Home() {
  const links = [
    {
      label: "Map View",
      href: "#",
      icon: (
        <Map className="text-neutral-700 dark:text-neutral-200 h-5 w-5 flex-shrink-0" />
      ),
    },
    {
      label: "Analytics",
      href: "#",
      icon: (
        <BarChart3 className="text-neutral-700 dark:text-neutral-200 h-5 w-5 flex-shrink-0" />
      ),
    },
    {
      label: "Business Advisor",
      href: "#",
      icon: (
        <MessageSquare className="text-neutral-700 dark:text-neutral-200 h-5 w-5 flex-shrink-0" />
      ),
    },
    {
      label: "Settings",
      href: "#",
      icon: (
        <Settings className="text-neutral-700 dark:text-neutral-200 h-5 w-5 flex-shrink-0" />
      ),
    },
  ];

  const [open, setOpen] = useState(false);

  return (
    <div className="flex flex-col md:flex-row bg-gray-100 dark:bg-neutral-800 w-full h-screen overflow-hidden">
      <Sidebar open={open} setOpen={setOpen}>
        <SidebarBody className="justify-between gap-10">
          <div className="flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
            {open ? <Logo /> : <LogoIcon />}
            <div className="mt-8 flex flex-col gap-2">
              {links.map((link, idx) => (
                <SidebarLink key={idx} link={link} />
              ))}
            </div>
          </div>
          <div>
            <div className="flex flex-col gap-2">
              <div className="text-xs text-neutral-500 dark:text-neutral-400">
                {open && "Atlanta Parking Detection"}
              </div>
            </div>
          </div>
        </SidebarBody>
      </Sidebar>
      <Dashboard />
    </div>
  );
}

const Logo = () => {
  return (
    <Link
      href="#"
      className="font-normal flex space-x-2 items-center text-sm text-black py-1 relative z-20"
    >
      <MapPin className="h-5 w-5 text-[#4ECDC4] flex-shrink-0" />
      <motion.span
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="font-medium text-black dark:text-white whitespace-pre"
      >
        <span className="text-[#4ECDC4]">Park</span>
        <span>Sight</span>
      </motion.span>
    </Link>
  );
};

const LogoIcon = () => {
  return (
    <Link
      href="#"
      className="font-normal flex space-x-2 items-center text-sm text-black py-1 relative z-20"
    >
      <MapPin className="h-5 w-5 text-[#4ECDC4] flex-shrink-0" />
    </Link>
  );
};

// Dashboard component - will be replaced with map later
const Dashboard = () => {
  return (
    <div className="flex flex-1">
      <div className="p-2 md:p-10 rounded-tl-2xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 flex flex-col gap-2 flex-1 w-full h-full">
        <div className="flex flex-col gap-4">
          <h1 className="text-2xl font-bold text-neutral-800 dark:text-neutral-200">
            ParkSight Dashboard
          </h1>
          <p className="text-neutral-600 dark:text-neutral-400">
            AI-powered parking detection for Atlanta
          </p>
        </div>

        {/* Stats Grid */}
        <div className="flex gap-2 mt-4">
          {[
            { label: "Lots Detected", value: "1,931" },
            { label: "Total Spaces", value: "517,826" },
            { label: "Coverage", value: "350 km²" },
            { label: "Avg Confidence", value: "92%" },
          ].map((stat, i) => (
            <div
              key={"stat" + i}
              className="h-24 w-full rounded-lg bg-gray-100 dark:bg-neutral-800 p-4 flex flex-col justify-between"
            >
              <div className="text-xs text-neutral-500 dark:text-neutral-400">
                {stat.label}
              </div>
              <div className="text-2xl font-bold text-neutral-800 dark:text-neutral-200">
                {stat.value}
              </div>
            </div>
          ))}
        </div>

        {/* Map Placeholder */}
        <div className="flex-1 mt-4 rounded-lg bg-gray-100 dark:bg-neutral-800 flex items-center justify-center">
          <div className="text-center">
            <Map className="h-16 w-16 text-neutral-400 mx-auto mb-4" />
            <p className="text-neutral-600 dark:text-neutral-400">
              Map view will be integrated here
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
