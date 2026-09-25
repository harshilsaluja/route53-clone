"use client";

import AppLayout from "@cloudscape-design/components/app-layout";
import ButtonDropdown from "@cloudscape-design/components/button-dropdown";
import BreadcrumbGroup, {
  type BreadcrumbGroupProps,
} from "@cloudscape-design/components/breadcrumb-group";
import Flashbar from "@cloudscape-design/components/flashbar";
import Icon from "@cloudscape-design/components/icon";
import SideNavigation, {
  type SideNavigationProps,
} from "@cloudscape-design/components/side-navigation";
import { applyDensity, applyMode, Density, Mode } from "@cloudscape-design/global-styles";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { useEffect, type ReactNode } from "react";
import { useNotifications } from "@/app/providers";
import { useBreadcrumbs } from "@/hooks/use-breadcrumbs";
import { logout } from "@/services/auth";
import type { User } from "@/types/api";

const navigationItems: SideNavigationProps.Item[] = [
  { type: "link", text: "Dashboard", href: "/route53/dashboard" },
  {
    type: "section",
    text: "DNS management",
    items: [
      { type: "link", text: "Hosted zones", href: "/route53/hosted-zones" },
      {
        type: "link",
        text: "Traffic policies",
        href: "/route53/traffic-policies",
      },
    ],
  },
  {
    type: "section",
    text: "Availability monitoring",
    items: [
      { type: "link", text: "Health checks", href: "/route53/health-checks" },
    ],
  },
  {
    type: "section",
    text: "Resolver",
    items: [
      { type: "link", text: "Resolver", href: "/route53/resolver" },
      { type: "link", text: "Profiles", href: "/route53/profiles" },
    ],
  },
];

function getActiveNavHref(pathname: string): string {
  if (pathname.startsWith("/route53/hosted-zones")) {
    return "/route53/hosted-zones";
  }
  if (pathname.startsWith("/route53/traffic-policies")) {
    return "/route53/traffic-policies";
  }
  if (pathname.startsWith("/route53/health-checks")) {
    return "/route53/health-checks";
  }
  if (pathname.startsWith("/route53/resolver")) {
    return "/route53/resolver";
  }
  if (pathname.startsWith("/route53/profiles")) {
    return "/route53/profiles";
  }
  if (pathname.startsWith("/route53/dashboard")) {
    return "/route53/dashboard";
  }
  return pathname;
}

function getContentType(
  pathname: string,
): "default" | "table" | "form" | "cards" {
  if (pathname.endsWith("/create") || pathname.endsWith("/edit")) {
    return "form";
  }
  if (
    pathname === "/route53/hosted-zones" ||
    /^\/route53\/hosted-zones\/[^/]+$/.test(pathname)
  ) {
    return "table";
  }
  return "default";
}

function buildBreadcrumbs(
  pathname: string,
  labels: Record<string, string>,
): BreadcrumbGroupProps.Item[] {
  const items: BreadcrumbGroupProps.Item[] = [
    { text: "Route 53", href: "/route53/hosted-zones" },
  ];

  if (pathname.includes("/hosted-zones")) {
    items.push({ text: "Hosted zones", href: "/route53/hosted-zones" });

    if (pathname === "/route53/hosted-zones/create") {
      items.push({ text: "Create hosted zone", href: pathname });
    } else {
      const parts = pathname.split("/").filter(Boolean);
      // parts: ['route53', 'hosted-zones', zoneId, ...]
      if (parts.length >= 3) {
        const zoneId = parts[2];
        const zonePath = `/route53/hosted-zones/${zoneId}`;
        const zoneLabel = labels[zoneId] || "Hosted zone";

        if (pathname === `${zonePath}/edit`) {
          items.push({ text: zoneLabel, href: zonePath });
          items.push({ text: "Edit", href: pathname });
        } else if (parts[3] === "records") {
          items.push({ text: zoneLabel, href: zonePath });
          if (parts[4] === "create") {
            items.push({ text: "Create record", href: pathname });
          } else if (parts[4]) {
            const recordId = parts[4];
            const recordPath = `${zonePath}/records/${recordId}`;
            const recordLabel = labels[recordId] || "Record";

            if (parts[5] === "edit") {
              items.push({ text: recordLabel, href: recordPath });
              items.push({ text: "Edit", href: pathname });
            } else {
              items.push({ text: recordLabel, href: recordPath });
            }
          }
        } else {
          items.push({ text: zoneLabel, href: zonePath });
        }
      }
    }
  } else if (pathname === "/route53/dashboard") {
    items.push({ text: "Dashboard", href: pathname });
  } else if (pathname === "/route53/health-checks") {
    items.push({ text: "Health checks", href: pathname });
  } else if (pathname === "/route53/traffic-policies") {
    items.push({ text: "Traffic policies", href: pathname });
  } else if (pathname === "/route53/resolver") {
    items.push({ text: "Resolver", href: pathname });
  } else if (pathname === "/route53/profiles") {
    items.push({ text: "Profiles", href: pathname });
  }

  return items;
}

export function Route53Shell({
  user,
  children,
}: {
  user: User;
  children: ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { notifications } = useNotifications();
  const { labels } = useBreadcrumbs();

  const logoutMutation = useMutation({
    mutationFn: logout,
    onSettled: () => {
      queryClient.clear();
      router.replace("/login");
    },
  });

  const follow = (href: string, event: { preventDefault: () => void }) => {
    event.preventDefault();
    router.push(href);
  };

  const activeNavHref = getActiveNavHref(pathname);
  const contentType = getContentType(pathname);

  useEffect(() => {
    applyMode(Mode.Dark);
    applyDensity(Density.Compact);
    document.body.classList.add("route53-console");
    return () => {
      applyMode(Mode.Light);
      applyDensity(Density.Comfortable);
      document.body.classList.remove("route53-console");
    };
  }, []);

  return (
    <>
      <div className="aws-top-nav" id="aws-top-nav">
        <div className="aws-global-header">
          <Link className="aws-wordmark" href="/route53/hosted-zones" aria-label="AWS home">aws<span /></Link>
          <div className="aws-service-tile" aria-hidden="true"><span>◇</span></div>
          <button className="aws-launcher" type="button" aria-label="Services menu (decorative)">{Array.from({ length: 9 }, (_, index) => <span key={index} />)}</button>
          <div className="aws-global-search" role="search" aria-label="Global search (decorative)"><span aria-hidden="true">⌕</span><span>Search</span><kbd>Alt+S</kbd></div>
          <div className="aws-header-utilities" aria-label="AWS console utilities">
            <button type="button" aria-label="CloudShell (decorative)"><Icon name="command-prompt" /></button>
            <button type="button" aria-label="Notifications (decorative)"><Icon name="notification" /></button>
            <button type="button" aria-label="Help (decorative)"><Icon name="status-info" /></button>
            <button type="button" aria-label="Settings (decorative)"><Icon name="settings" /></button>
          </div>
          <div className="aws-region">Global <span aria-hidden="true">▾</span></div>
          <div className="aws-account-menu"><ButtonDropdown
            items={[{ id: "email", text: user.email, disabled: true }, { id: "logout", text: "Sign out" }]}
            onItemClick={({ detail }) => { if (detail.id === "logout" && !logoutMutation.isPending) logoutMutation.mutate(); }}
          >{user.display_name}</ButtonDropdown></div>
        </div>
      </div>
      <AppLayout
        contentType={contentType}
        headerSelector="#aws-top-nav"
        stickyNotifications
        navigation={
          <SideNavigation
            header={{ href: "/route53/hosted-zones", text: "Route 53" }}
            activeHref={activeNavHref}
            items={navigationItems}
            onFollow={(event) => {
              if (!event.detail.external) follow(event.detail.href, event);
            }}
          />
        }
        breadcrumbs={
          <BreadcrumbGroup
            items={buildBreadcrumbs(pathname, labels)}
            onFollow={(event) => follow(event.detail.href, event)}
          />
        }
        notifications={<Flashbar items={notifications} />}
        content={children}
        toolsHide
      />
    </>
  );
}
