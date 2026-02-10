#!/usr/bin/env python3

import requests
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress
from rich import box
import sys

console = Console()

class GitHubStats:
    def __init__(self, username, token=None):
        self.username = username
        self.token = token
        self.headers = {}
        if token:
            self.headers['Authorization'] = f'token {token}'
        self.base_url = 'https://api.github.com'
    
    def get_user_repos(self):
        repos = []
        page = 1
        while True:
            url = f'{self.base_url}/users/{self.username}/repos?per_page=100&page={page}'
            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                console.print(f"[red]Error fetching repos: {response.status_code}[/red]")
                break
            data = response.json()
            if not data:
                break
            repos.extend(data)
            page += 1
        return repos
    
    def get_commit_activity(self, repo_name):
        url = f'{self.base_url}/repos/{self.username}/{repo_name}/commits'
        params = {'author': self.username, 'per_page': 100}
        commits = []
        page = 1
        
        while True:
            params['page'] = page
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code != 200:
                break
            data = response.json()
            if not data:
                break
            commits.extend(data)
            
            if 'Link' not in response.headers:
                break
            if 'rel="next"' not in response.headers['Link']:
                break
                
            page += 1
            
        return commits
    
    def calculate_streak(self, commit_dates):
        if not commit_dates:
            return 0, 0, None, None, 0, None, None
        
        dates = sorted(set(commit_dates), reverse=True)
        current_streak = 0
        current_start = None
        current_end = None
        max_streak = 0
        max_start = None
        max_end = None
        
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        
        if dates[0] == today or dates[0] == yesterday:
            current_streak = 1
            current_end = dates[0]
            current_start = dates[0]
            
            for i in range(1, len(dates)):
                if dates[i] == current_start - timedelta(days=1):
                    current_streak += 1
                    current_start = dates[i]
                else:
                    break
        
        temp_streak = 1
        temp_end = dates[0]
        temp_start = dates[0]
        
        for i in range(1, len(dates)):
            if dates[i] == temp_start - timedelta(days=1):
                temp_streak += 1
                temp_start = dates[i]
            else:
                if temp_streak > max_streak:
                    max_streak = temp_streak
                    max_start = temp_start
                    max_end = temp_end
                temp_streak = 1
                temp_end = dates[i]
                temp_start = dates[i]
        
        if temp_streak > max_streak:
            max_streak = temp_streak
            max_start = temp_start
            max_end = temp_end
        
        if current_streak > max_streak:
            max_streak = current_streak
            max_start = current_start
            max_end = current_end
        
        return current_streak, current_start, current_end, max_streak, max_start, max_end
    
    def analyze(self):
        console.print(Panel.fit(
            f"[bold cyan]GitHub Statistics for {self.username}[/bold cyan]",
            border_style="cyan"
        ))
        
        repos = self.get_user_repos()
        console.print(f"\n[yellow]Found {len(repos)} repositories[/yellow]\n")
        
        all_commits = []
        commit_dates = []
        languages = Counter()
        repo_commits = defaultdict(int)
        weekday_commits = Counter()
        hour_commits = Counter()
        
        with Progress() as progress:
            task = progress.add_task("[cyan]Analyzing commits...", total=len(repos))
            
            for repo in repos:
                if repo['language']:
                    languages[repo['language']] += 1
                
                commits = self.get_commit_activity(repo['name'])
                repo_commits[repo['name']] = len(commits)
                
                for commit in commits:
                    all_commits.append(commit)
                    if commit.get('commit', {}).get('author', {}).get('date'):
                        date_str = commit['commit']['author']['date']
                        dt = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ')
                        commit_dates.append(dt.date())
                        weekday_commits[dt.strftime('%A')] += 1
                        hour_commits[dt.hour] += 1
                
                progress.update(task, advance=1)
        
        current_streak, current_start, current_end, max_streak, max_start, max_end = self.calculate_streak(commit_dates)
        
        self.display_results(
            len(all_commits),
            current_streak,
            current_start,
            current_end,
            max_streak,
            max_start,
            max_end,
            languages,
            repo_commits,
            weekday_commits,
            hour_commits,
            commit_dates
        )
    
    def display_results(self, total_commits, current_streak, current_start, current_end,
                       max_streak, max_start, max_end, languages, repo_commits, 
                       weekday_commits, hour_commits, commit_dates):
        
        stats_table = Table(show_header=False, box=box.ROUNDED, border_style="blue")
        stats_table.add_column(style="cyan bold")
        stats_table.add_column(style="white")
        
        if current_streak > 0:
            streak_info = f"[bold green]{current_streak} days[/bold green]"
            if current_start and current_end:
                streak_info += f"\n[dim]{current_start} → {current_end}[/dim]"
            stats_table.add_row("🔥 Current Streak", streak_info)
        else:
            stats_table.add_row("🔥 Current Streak", "[bold red]0 days[/bold red]")
        
        if max_streak > 0:
            max_streak_info = f"[bold yellow]{max_streak} days[/bold yellow]"
            if max_start and max_end:
                max_streak_info += f"\n[dim]{max_start} → {max_end}[/dim]"
            stats_table.add_row("🏆 Max Streak", max_streak_info)
        
        stats_table.add_row("📊 Total Commits", f"[bold magenta]{total_commits}[/bold magenta]")
        
        if commit_dates:
            stats_table.add_row("📅 First Commit", str(min(commit_dates)))
            stats_table.add_row("📅 Last Commit", str(max(commit_dates)))
        
        console.print("\n")
        console.print(Panel(stats_table, title="[bold]Overview[/bold]", border_style="blue"))
        
        if languages:
            lang_table = Table(title="[bold]Top Languages[/bold]", box=box.SIMPLE, border_style="green")
            lang_table.add_column("Language", style="cyan")
            lang_table.add_column("Repositories", justify="right", style="magenta")
            
            for lang, count in languages.most_common(10):
                lang_table.add_row(lang, str(count))
            
            console.print("\n")
            console.print(lang_table)
        
        if repo_commits:
            repo_table = Table(title="[bold]Most Active Repositories[/bold]", box=box.SIMPLE, border_style="yellow")
            repo_table.add_column("Repository", style="cyan")
            repo_table.add_column("Commits", justify="right", style="magenta")
            
            for repo, count in sorted(repo_commits.items(), key=lambda x: x[1], reverse=True)[:10]:
                repo_table.add_row(repo, str(count))
            
            console.print("\n")
            console.print(repo_table)
        
        if weekday_commits:
            weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            weekday_table = Table(title="[bold]Activity by Day of Week[/bold]", box=box.SIMPLE, border_style="cyan")
            weekday_table.add_column("Day", style="cyan")
            weekday_table.add_column("Commits", justify="right", style="magenta")
            weekday_table.add_column("Bar", style="green")
            
            max_commits = max(weekday_commits.values()) if weekday_commits else 1
            for day in weekday_order:
                count = weekday_commits.get(day, 0)
                bar = "█" * int((count / max_commits) * 30)
                weekday_table.add_row(day, str(count), bar)
            
            console.print("\n")
            console.print(weekday_table)
        
        if hour_commits:
            console.print("\n")
            console.print(Panel.fit("[bold cyan]Most Active Hour:[/bold cyan] " + 
                                   f"[bold yellow]{max(hour_commits, key=hour_commits.get)}:00[/bold yellow]",
                                   border_style="cyan"))

def main():
    if len(sys.argv) < 2:
        console.print("[red]Usage: python github-stats.py <username> [token][/red]")
        console.print("[yellow]Token is optional but recommended to avoid rate limits[/yellow]")
        sys.exit(1)
    
    username = sys.argv[1]
    token = sys.argv[2] if len(sys.argv) > 2 else None
    
    stats = GitHubStats(username, token)
    stats.analyze()

if __name__ == '__main__':
    main()