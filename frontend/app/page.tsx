"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated, hasPizzeriaSelected, getPizzeriaId } from "@/lib/auth";

export default function RootPage() {
  const router = useRouter();

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
    } else if (!hasPizzeriaSelected()) {
      router.replace("/selector");
    } else {
      router.replace(`/${getPizzeriaId()}/dashboard`);
    }
  }, [router]);

  return null;
}
