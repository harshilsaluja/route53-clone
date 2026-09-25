"use client";

import AppLayout from "@cloudscape-design/components/app-layout";
import BreadcrumbGroup, {
  type BreadcrumbGroupProps,
} from "@cloudscape-design/components/breadcrumb-group";
import Flashbar from "@cloudscape-design/components/flashbar";
import SideNavigation, {
  type SideNavigationProps,
} from "@cloudscape-design/components/side-navigation";
import TopNavigation from "@cloudscape-design/components/top-navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useNotifications } from "@/app/providers";
import { logout } from "@/services/auth";
import type { User } from "@/types/api";

const navigationItems: SideNavigationProps.Item[] = [
  { type: "link", text: "Dashboard", href: "/route53/dashboard" },
  { type: "link", text: "Hosted zones", href: "/route53/hosted-zones" },
  { type: "link", text: "Health checks", href: "/route53/health-checks" },
  { type: "link", text: "Traffic policies", href: "/route53/traffic-policies" },
  { type: "link", text: "Resolver", href: "/route53/resolver" },
  { type: "link", text: "Profiles", href: "/route53/profiles" },
];

function breadcrumbs(pathname: string): BreadcrumbGroupProps.Item[] {
  const items: BreadcrumbGroupProps.Item[] = [
    { text: "Route 53", href: "/route53/hosted-zones" },
  ];
  if (pathname.includes("/hosted-zones")) {
    items.push({ text: "Hosted zones", href: "/route53/hosted-zones" });
    if (pathname.endsWith("/create")) {
      if (pathname.includes("/records/create")) {
        const zonePath = pathname.replace(/\/records\/create$/, "");
        items.push({ text: "Hosted zone details", href: zonePath });
        items.push({ text: "Create record", href: pathname });
      } else {
        items.push({ text: "Create hosted zone", href: pathname });
      }
    } else {
      const parts = pathname.split("/").filter(Boolean);
      if (parts.length >= 3) {
        const zonePath = `/route53/hosted-zones/${parts[2]}`;
        items.push({ text: "Hosted zone details", href: zonePath });
      }
      if (parts[3] === "records" && parts[4]) {
        const recordPath = `/route53/hosted-zones/${parts[2]}/records/${parts[4]}`;
        items.push({ text: "Record details", href: recordPath });
      }
      if (pathname.endsWith("/edit") && parts[3] === "records") {
        items.push({ text: "Edit record", href: pathname });
      } else if (pathname.endsWith("/edit")) {
        items.push({ text: "Edit", href: pathname });
      }
    }
  } else {
    const label = navigationItems.find(
      (item) => item.type === "link" && item.href === pathname,
    );
    if (label && label.type === "link") {
      items.push({ text: label.text, href: pathname });
    }
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

  return (
    <>
      <div className="aws-top-nav">
        <TopNavigation
          identity={{
            href: "/route53/hosted-zones",
            title: "AWS  |  Route 53 Clone",
            onFollow: (event) => follow("/route53/hosted-zones", event),
          }}
          utilities={[
            {
              type: "menu-dropdown",
              text: user.display_name,
              description: user.email,
              iconName: "user-profile",
              items: [{ id: "logout", text: "Sign out" }],
              onItemClick: ({ detail }) => {
                if (detail.id === "logout" && !logoutMutation.isPending) {
                  logoutMutation.mutate();
                }
              },
            },
          ]}
        />
      </div>
      <AppLayout
        navigation={
          <SideNavigation
            header={{ href: "/route53/hosted-zones", text: "Route 53" }}
            activeHref={pathname}
            items={navigationItems}
            onFollow={(event) => {
              if (!event.detail.external) follow(event.detail.href, event);
            }}
          />
        }
        breadcrumbs={
          <BreadcrumbGroup
            items={breadcrumbs(pathname)}
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
