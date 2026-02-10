import { Octokit } from '@octokit/rest';
import * as fs from 'fs';

interface CommitData {
  date: Date;
  repo: string;
}

interface Stats {
  currentStreak: number;
  currentStreakStart: Date | null;
  currentStreakEnd: Date | null;
  maxStreak: number;
  maxStreakStart: Date | null;
  maxStreakEnd: Date | null;
  totalCommits: number;
  languages: Map<string, number>;
  repoCommits: Map<string, number>;
  weekdayCommits: Map<string, number>;
  hourCommits: Map<number, number>;
  firstCommit: Date | null;
  lastCommit: Date | null;
}

class GitHubStats {
  private octokit: Octokit;
  private username: string;

  constructor(username: string, token?: string) {
    this.username = username;
    this.octokit = new Octokit({ auth: token });
  }

  async getRepos() {
    const repos = [];
    let page = 1;
    
    while (true) {
      const response = await this.octokit.repos.listForUser({
        username: this.username,
        per_page: 100,
        page
      });
      
      if (response.data.length === 0) break;
      repos.push(...response.data);
      page++;
    }
    
    return repos;
  }

  async getCommits(repo: string) {
    const commits = [];
    let page = 1;
    
    while (true) {
      try {
        const response = await this.octokit.repos.listCommits({
          owner: this.username,
          repo,
          per_page: 100,
          page
        });
        
        if (response.data.length === 0) break;
        
        for (const commit of response.data) {
          if (commit.author?.login === this.username || 
              commit.commit?.author?.email?.includes(this.username) ||
              commit.commit?.author?.name === this.username ||
              commit.committer?.login === this.username) {
            commits.push(commit);
          }
        }
        
        if (response.data.length < 100) break;
        page++;
      } catch (error) {
        break;
      }
    }
    
    return commits;
  }

  calculateStreak(dates: Date[]): {
    currentStreak: number;
    currentStart: Date | null;
    currentEnd: Date | null;
    maxStreak: number;
    maxStart: Date | null;
    maxEnd: Date | null;
  } {
    if (dates.length === 0) {
      return {
        currentStreak: 0,
        currentStart: null,
        currentEnd: null,
        maxStreak: 0,
        maxStart: null,
        maxEnd: null
      };
    }

    const uniqueDates = Array.from(new Set(dates.map(d => d.toDateString())))
      .map(d => new Date(d))
      .sort((a, b) => b.getTime() - a.getTime());

    let currentStreak = 0;
    let currentStart: Date | null = null;
    let currentEnd: Date | null = null;
    let maxStreak = 0;
    let maxStart: Date | null = null;
    let maxEnd: Date | null = null;

    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    const firstDate = new Date(uniqueDates[0]);
    firstDate.setHours(0, 0, 0, 0);

    if (firstDate.getTime() === today.getTime() || firstDate.getTime() === yesterday.getTime()) {
      currentStreak = 1;
      currentEnd = uniqueDates[0];
      currentStart = uniqueDates[0];

      for (let i = 1; i < uniqueDates.length; i++) {
        const expectedDate = new Date(currentStart);
        expectedDate.setDate(expectedDate.getDate() - 1);
        
        const actualDate = new Date(uniqueDates[i]);
        actualDate.setHours(0, 0, 0, 0);
        expectedDate.setHours(0, 0, 0, 0);

        if (actualDate.getTime() === expectedDate.getTime()) {
          currentStreak++;
          currentStart = uniqueDates[i];
        } else {
          break;
        }
      }
    }

    let tempStreak = 1;
    let tempEnd = uniqueDates[0];
    let tempStart = uniqueDates[0];

    for (let i = 1; i < uniqueDates.length; i++) {
      const expectedDate = new Date(tempStart);
      expectedDate.setDate(expectedDate.getDate() - 1);
      
      const actualDate = new Date(uniqueDates[i]);
      actualDate.setHours(0, 0, 0, 0);
      expectedDate.setHours(0, 0, 0, 0);

      if (actualDate.getTime() === expectedDate.getTime()) {
        tempStreak++;
        tempStart = uniqueDates[i];
      } else {
        if (tempStreak > maxStreak) {
          maxStreak = tempStreak;
          maxStart = tempStart;
          maxEnd = tempEnd;
        }
        tempStreak = 1;
        tempEnd = uniqueDates[i];
        tempStart = uniqueDates[i];
      }
    }

    if (tempStreak > maxStreak) {
      maxStreak = tempStreak;
      maxStart = tempStart;
      maxEnd = tempEnd;
    }

    if (currentStreak > maxStreak) {
      maxStreak = currentStreak;
      maxStart = currentStart;
      maxEnd = currentEnd;
    }

    return { currentStreak, currentStart, currentEnd, maxStreak, maxStart, maxEnd };
  }

  async analyze(): Promise<Stats> {
    console.log(`Fetching repositories for ${this.username}...`);
    const repos = await this.getRepos();
    console.log(`Found ${repos.length} repositories`);

    const commitDates: Date[] = [];
    const languages = new Map<string, number>();
    const repoCommits = new Map<string, number>();
    const weekdayCommits = new Map<string, number>();
    const hourCommits = new Map<number, number>();

    for (const repo of repos) {
      if (repo.language) {
        languages.set(repo.language, (languages.get(repo.language) || 0) + 1);
      }

      console.log(`Processing ${repo.name}...`);
      const commits = await this.getCommits(repo.name);
      repoCommits.set(repo.name, commits.length);

      for (const commit of commits) {
        if (commit.commit?.author?.date) {
          const date = new Date(commit.commit.author.date);
          commitDates.push(date);
          
          const weekday = date.toLocaleDateString('en-US', { weekday: 'long' });
          weekdayCommits.set(weekday, (weekdayCommits.get(weekday) || 0) + 1);
          
          hourCommits.set(date.getHours(), (hourCommits.get(date.getHours()) || 0) + 1);
        }
      }
    }

    const streak = this.calculateStreak(commitDates);

    return {
      currentStreak: streak.currentStreak,
      currentStreakStart: streak.currentStart,
      currentStreakEnd: streak.currentEnd,
      maxStreak: streak.maxStreak,
      maxStreakStart: streak.maxStart,
      maxStreakEnd: streak.maxEnd,
      totalCommits: commitDates.length,
      languages,
      repoCommits,
      weekdayCommits,
      hourCommits,
      firstCommit: commitDates.length > 0 ? new Date(Math.min(...commitDates.map(d => d.getTime()))) : null,
      lastCommit: commitDates.length > 0 ? new Date(Math.max(...commitDates.map(d => d.getTime()))) : null
    };
  }

  generateHTML(stats: Stats): string {
    const formatDate = (date: Date | null) => date ? date.toLocaleDateString() : 'N/A';
    
    const weekdayOrder = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
    const maxWeekdayCommits = Math.max(...Array.from(stats.weekdayCommits.values()), 1);
    
    const topLanguages = Array.from(stats.languages.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10);
    
    const topRepos = Array.from(stats.repoCommits.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10);
    
    const maxHourCommits = Math.max(...Array.from(stats.hourCommits.values()), 1);
    const mostActiveHour = Array.from(stats.hourCommits.entries())
      .sort((a, b) => b[1] - a[1])[0];

    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GitHub Stats - ${this.username}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            color: white;
            margin-bottom: 40px;
        }
        
        .header h1 {
            font-size: 3em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .header p {
            font-size: 1.2em;
            opacity: 0.9;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.3);
        }
        
        .card-title {
            font-size: 1.1em;
            color: #666;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .card-value {
            font-size: 2.5em;
            font-weight: bold;
            color: #333;
            margin-bottom: 10px;
        }
        
        .card-subtitle {
            color: #999;
            font-size: 0.9em;
        }
        
        .streak-card {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
        }
        
        .streak-card .card-title,
        .streak-card .card-subtitle {
            color: rgba(255,255,255,0.9);
        }
        
        .streak-card .card-value {
            color: white;
        }
        
        .max-streak-card {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
        }
        
        .max-streak-card .card-title,
        .max-streak-card .card-subtitle {
            color: rgba(255,255,255,0.9);
        }
        
        .max-streak-card .card-value {
            color: white;
        }
        
        .table-card {
            grid-column: 1 / -1;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        th {
            text-align: left;
            padding: 12px;
            background: #f5f5f5;
            color: #666;
            font-weight: 600;
        }
        
        td {
            padding: 12px;
            border-bottom: 1px solid #eee;
        }
        
        tr:hover {
            background: #f9f9f9;
        }
        
        .bar {
            height: 20px;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            border-radius: 10px;
            transition: width 0.3s ease;
        }
        
        .bar-container {
            width: 100%;
            background: #f0f0f0;
            border-radius: 10px;
            overflow: hidden;
        }
        
        .emoji {
            font-size: 1.3em;
        }
        
        .date-range {
            font-size: 0.5em;
            font-weight: normal;
            opacity: 0.8;
            display: block;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 GitHub Statistics</h1>
            <p>@${this.username}</p>
        </div>
        
        <div class="stats-grid">
            <div class="card streak-card">
                <div class="card-title"><span class="emoji">🔥</span> Current Streak</div>
                <div class="card-value">
                    ${stats.currentStreak} days
                    ${stats.currentStreakStart ? `<span class="date-range">${formatDate(stats.currentStreakStart)} → ${formatDate(stats.currentStreakEnd)}</span>` : ''}
                </div>
            </div>
            
            <div class="card max-streak-card">
                <div class="card-title"><span class="emoji">🏆</span> Max Streak</div>
                <div class="card-value">
                    ${stats.maxStreak} days
                    ${stats.maxStreakStart ? `<span class="date-range">${formatDate(stats.maxStreakStart)} → ${formatDate(stats.maxStreakEnd)}</span>` : ''}
                </div>
            </div>
            
            <div class="card">
                <div class="card-title"><span class="emoji">📊</span> Total Commits</div>
                <div class="card-value">${stats.totalCommits.toLocaleString()}</div>
            </div>
            
            <div class="card">
                <div class="card-title"><span class="emoji">📅</span> First Commit</div>
                <div class="card-value" style="font-size: 1.5em;">${formatDate(stats.firstCommit)}</div>
            </div>
            
            <div class="card">
                <div class="card-title"><span class="emoji">📅</span> Last Commit</div>
                <div class="card-value" style="font-size: 1.5em;">${formatDate(stats.lastCommit)}</div>
            </div>
            
            <div class="card">
                <div class="card-title"><span class="emoji">⏰</span> Most Active Hour</div>
                <div class="card-value" style="font-size: 1.8em;">${mostActiveHour ? `${mostActiveHour[0]}:00` : 'N/A'}</div>
                <div class="card-subtitle">${mostActiveHour ? `${mostActiveHour[1]} commits` : ''}</div>
            </div>
        </div>
        
        <div class="stats-grid">
            <div class="card table-card">
                <div class="card-title"><span class="emoji">💻</span> Top Languages</div>
                <table>
                    <thead>
                        <tr>
                            <th>Language</th>
                            <th>Repositories</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${topLanguages.map(([lang, count]) => `
                            <tr>
                                <td><strong>${lang}</strong></td>
                                <td>${count}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
            
            <div class="card table-card">
                <div class="card-title"><span class="emoji">📈</span> Most Active Repositories</div>
                <table>
                    <thead>
                        <tr>
                            <th>Repository</th>
                            <th>Commits</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${topRepos.map(([repo, count]) => `
                            <tr>
                                <td><strong>${repo}</strong></td>
                                <td>${count}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
            
            <div class="card table-card">
                <div class="card-title"><span class="emoji">📅</span> Activity by Day of Week</div>
                <table>
                    <thead>
                        <tr>
                            <th>Day</th>
                            <th>Commits</th>
                            <th>Activity</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${weekdayOrder.map(day => {
                            const count = stats.weekdayCommits.get(day) || 0;
                            const percentage = (count / maxWeekdayCommits) * 100;
                            return `
                                <tr>
                                    <td><strong>${day}</strong></td>
                                    <td>${count}</td>
                                    <td>
                                        <div class="bar-container">
                                            <div class="bar" style="width: ${percentage}%"></div>
                                        </div>
                                    </td>
                                </tr>
                            `;
                        }).join('')}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</body>
</html>`;
  }
}

async function main() {
  const args = process.argv.slice(2);
  
  if (args.length < 1) {
    console.error('Usage: ts-node github-stats.ts <username> [token]');
    process.exit(1);
  }
  
  const username = args[0];
  const token = args[1];
  
  const stats = new GitHubStats(username, token);
  const data = await stats.analyze();
  const html = stats.generateHTML(data);
  
  const filename = `github-stats-${username}.html`;
  fs.writeFileSync(filename, html);
  
  console.log(`\n✅ Stats generated: ${filename}`);
  console.log(`🔥 Current streak: ${data.currentStreak} days`);
  console.log(`🏆 Max streak: ${data.maxStreak} days`);
  console.log(`📊 Total commits: ${data.totalCommits}`);
}

main().catch(console.error);