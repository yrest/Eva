#!/usr/bin/env python3
"""CLI tool for managing Eva's MCP server registry."""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from storage import storage


def add_server(args):
    """Register a new MCP server."""
    try:
        server = storage.add_server(
            name=args.name,
            type=args.type,
            url=args.url,
            auth_token=args.token
        )

        print(f"\n✅ Registered: {server['name']}")
        print(f"   ID:   {server['id']}")
        print(f"   Type: {server['type']}")
        print(f"   URL:  {server['url']}")
        print()

    except ValueError as e:
        print(f"\n❌ Error: {e}\n")
        sys.exit(1)


def list_servers(args):
    """List all registered servers."""
    servers = storage.list_servers(enabled_only=not args.all)

    if not servers:
        print("\n📋 No servers registered yet.\n")
        return

    print(f"\n📋 Registered Services ({len(servers)}):\n")

    # Group by type
    by_type = {}
    for s in servers:
        by_type.setdefault(s['type'], []).append(s)

    for server_type in sorted(by_type.keys()):
        print(f"  {server_type.upper()}:")
        for s in by_type[server_type]:
            status = "✅" if s.get("enabled") else "❌"
            print(f"    {status} {s['name']}")
            print(f"       ID:  {s['id']}")
            print(f"       URL: {s['url']}")
        print()


def remove_server(args):
    """Remove a server from registry."""
    # Try to find by ID or name
    server = storage.get_server(args.server)
    if not server:
        server = storage.get_server_by_name(args.server)

    if not server:
        print(f"\n❌ Server '{args.server}' not found\n")
        sys.exit(1)

    if not args.yes:
        confirm = input(f"Remove server '{server['name']}'? [y/N] ")
        if confirm.lower() != 'y':
            print("Cancelled.")
            return

    storage.remove_server(server['id'])
    print(f"\n✅ Removed: {server['name']}\n")


def enable_server(args):
    """Enable a server."""
    server = storage.get_server(args.server)
    if not server:
        server = storage.get_server_by_name(args.server)

    if not server:
        print(f"\n❌ Server '{args.server}' not found\n")
        sys.exit(1)

    storage.update_server(server['id'], {"enabled": True})
    print(f"\n✅ Enabled: {server['name']}\n")


def disable_server(args):
    """Disable a server."""
    server = storage.get_server(args.server)
    if not server:
        server = storage.get_server_by_name(args.server)

    if not server:
        print(f"\n❌ Server '{args.server}' not found\n")
        sys.exit(1)

    storage.update_server(server['id'], {"enabled": False})
    print(f"\n⏸️  Disabled: {server['name']}\n")


def show_server(args):
    """Show detailed server info."""
    server = storage.get_server(args.server)
    if not server:
        server = storage.get_server_by_name(args.server)

    if not server:
        print(f"\n❌ Server '{args.server}' not found\n")
        sys.exit(1)

    status = "✅ Enabled" if server.get("enabled") else "❌ Disabled"
    print(f"\n📡 {server['name']} ({status})")
    print(f"   ID:           {server['id']}")
    print(f"   Type:         {server['type']}")
    print(f"   URL:          {server['url']}")
    print(f"   Registered:   {server['registered_at']}")

    if server.get('capabilities'):
        print(f"   Capabilities: {server['capabilities']}")

    print()


# Collection schema management

def add_collection(args):
    """Register a collection schema."""
    import json

    try:
        schema = json.loads(args.schema)
    except json.JSONDecodeError:
        print("\n❌ Invalid JSON schema\n")
        sys.exit(1)

    collection = storage.register_collection_schema(
        collection_name=args.name,
        schema=schema,
        description=args.description
    )

    print(f"\n✅ Registered collection schema: {collection['name']}")
    print(f"   Description: {collection.get('description', 'None')}")
    print(f"   Fields: {len(schema)}")
    for field, field_type in schema.items():
        print(f"     - {field}: {field_type}")
    print()


def list_collections(args):
    """List all registered collection schemas."""
    collections = storage.list_collection_schemas()

    if not collections:
        print("\n📋 No collection schemas registered yet.\n")
        return

    print(f"\n📋 Registered Collections ({len(collections)}):\n")

    for name, info in collections.items():
        print(f"  📦 {name}")
        print(f"     Description: {info.get('description', 'No description')}")
        print(f"     Fields: {', '.join(info.get('schema', {}).keys())}")
        print()


def remove_collection(args):
    """Remove a collection schema."""
    if not args.yes:
        confirm = input(f"Remove collection schema '{args.name}'? [y/N] ")
        if confirm.lower() != 'y':
            print("Cancelled.")
            return

    success = storage.remove_collection_schema(args.name)
    if success:
        print(f"\n✅ Removed collection schema: {args.name}\n")
    else:
        print(f"\n❌ Collection schema '{args.name}' not found\n")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Eva MCP Server Registry Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Register filesystem server
  %(prog)s add "Office Desktop" filesystem http://192.168.1.10:8005 read-token-123

  # Register embedding service
  %(prog)s add "Local Ollama" embedding http://localhost:8006 embed-token

  # List all servers
  %(prog)s list

  # Show server details
  %(prog)s show "Office Desktop"

  # Disable a server
  %(prog)s disable "Office Desktop"

  # Remove a server
  %(prog)s remove "Office Desktop"

  # Register collection schemas
  %(prog)s add-collection abc '{"sender":"str", "subject":"str", "date":"datetime"}' --description "Email archive"
  %(prog)s add-collection teams_messages '{"sender":"str", "channel":"str", "message":"str", "date":"datetime"}' --description "Teams chat history"

  # List collections
  %(prog)s list-collections

  # Remove collection schema
  %(prog)s remove-collection abc
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command')

    # Add command
    add_parser = subparsers.add_parser('add', help='Register a new MCP server')
    add_parser.add_argument('name', help='Server name (e.g., "Office Desktop")')
    add_parser.add_argument('type', choices=['filesystem', 'embedding', 'vector'],
                           help='Server type')
    add_parser.add_argument('url', help='Server URL (e.g., http://192.168.1.10:8005)')
    add_parser.add_argument('token', help='Authentication token')
    add_parser.set_defaults(func=add_server)

    # List command
    list_parser = subparsers.add_parser('list', help='List registered servers')
    list_parser.add_argument('-a', '--all', action='store_true',
                            help='Include disabled servers')
    list_parser.set_defaults(func=list_servers)

    # Show command
    show_parser = subparsers.add_parser('show', help='Show server details')
    show_parser.add_argument('server', help='Server ID or name')
    show_parser.set_defaults(func=show_server)

    # Remove command
    remove_parser = subparsers.add_parser('remove', help='Remove a server')
    remove_parser.add_argument('server', help='Server ID or name')
    remove_parser.add_argument('-y', '--yes', action='store_true',
                              help='Skip confirmation')
    remove_parser.set_defaults(func=remove_server)

    # Enable command
    enable_parser = subparsers.add_parser('enable', help='Enable a server')
    enable_parser.add_argument('server', help='Server ID or name')
    enable_parser.set_defaults(func=enable_server)

    # Disable command
    disable_parser = subparsers.add_parser('disable', help='Disable a server')
    disable_parser.add_argument('server', help='Server ID or name')
    disable_parser.set_defaults(func=disable_server)

    # Collection schema commands
    collection_parser = subparsers.add_parser('add-collection', help='Register a collection schema')
    collection_parser.add_argument('name', help='Collection name (e.g., "abc")')
    collection_parser.add_argument('schema', help='JSON schema (e.g., \'{"sender":"str", "date":"datetime"}\')')
    collection_parser.add_argument('--description', default='', help='Description of the collection')
    collection_parser.set_defaults(func=add_collection)

    list_coll_parser = subparsers.add_parser('list-collections', help='List registered collection schemas')
    list_coll_parser.set_defaults(func=list_collections)

    remove_coll_parser = subparsers.add_parser('remove-collection', help='Remove a collection schema')
    remove_coll_parser.add_argument('name', help='Collection name')
    remove_coll_parser.add_argument('-y', '--yes', action='store_true', help='Skip confirmation')
    remove_coll_parser.set_defaults(func=remove_collection)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
