#!/usr/bin/env node

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

class GitStats {
    constructor(repoPath = '.') {
        this.repoPath = repoPath;
        this.isGitRepo = this.checkGitRepo();
    }

getAllFiles(dir, fileList = []) {
    const entries = fs.readdirSync(dir, { withFileTypes: true });

    for (const entry of entries) {
        const fullPath = path.join(dir, entry.name);

        if (
            entry.name === '.git' ||
            entry.name === 'node_modules' ||
            entry.name === 'dist' ||
            entry.name === 'build'
        ) continue;

        if (entry.isDirectory()) {
            this.getAllFiles(fullPath, fileList);
        } else {
            fileList.push(fullPath);
        }
    }

    return fileList;
}

    checkGitRepo() {
        try {
            execSync('git rev-parse --git-dir', { 
                cwd: this.repoPath, 
                stdio: 'pipe' 
            });
            return true;
        } catch {
            return false;
        }
    }

    exec(command) {
        try {
            return execSync(command, {
                cwd: this.repoPath,
                encoding: 'utf8',
                stdio: 'pipe'
            }).trim();
        } catch (error) {
            return '';
        }
    }

    getRepoName() {
        const remote = this.exec('git config --get remote.origin.url');
        if (remote) {
            const match = remote.match(/\/([^\/]+?)(\.git)?$/);
            return match ? match[1] : path.basename(this.repoPath);
        }
        return path.basename(path.resolve(this.repoPath));
    }

    getCurrentBranch() {
        return this.exec('git rev-parse --abbrev-ref HEAD');
    }

    getTotalCommits() {
        const result = this.exec('git rev-list --count HEAD');
        return result ? parseInt(result) : 0;
    }

    getCommitsByAuthor() {
        const output = this.exec('git shortlog -sn --all --no-merges');
        const authors = [];
        
        output.split('\n').forEach(line => {
            const match = line.trim().match(/^(\d+)\s+(.+)$/);
            if (match) {
                authors.push({
                    commits: parseInt(match[1]),
                    name: match[2]
                });
            }
        });
        
        return authors;
    }

    getFileStats() {
        const output = this.exec('git ls-files');
        if (!output) {
            return { total: 0, extensions: [] };
        }
        
        const files = output.split('\n').filter(f => f.trim());
        
        const extensions = {};
        files.forEach(file => {
            const ext = path.extname(file) || 'no extension';
            extensions[ext] = (extensions[ext] || 0) + 1;
        });
        
        return {
            total: files.length,
            extensions: Object.entries(extensions)
                .map(([ext, count]) => ({ ext, count }))
                .sort((a, b) => b.count - a.count)
        };
    }

    getLanguageStats() {
    const files = this.getAllFiles(this.repoPath);

    const languages = {
        JavaScript: ['.js', '.jsx', '.mjs'],
        TypeScript: ['.ts', '.tsx'],
        Python: ['.py'],
        Java: ['.java'],
        'C/C++': ['.c', '.cpp', '.h', '.hpp', '.cc', '.cxx'],
        'C#': ['.cs'],
        Go: ['.go'],
        Rust: ['.rs'],
        PHP: ['.php'],
        Ruby: ['.rb'],
        HTML: ['.html', '.htm'],
        CSS: ['.css', '.scss', '.sass', '.less'],
        Shell: ['.sh', '.bash'],
        SQL: ['.sql'],
        Markdown: ['.md', '.markdown'],
        JSON: ['.json'],
        XML: ['.xml'],
        YAML: ['.yml', '.yaml'],
        PowerShell: ['.ps1', '.psm1'],
        Batch: ['.bat', '.cmd']
    };

    const langCount = {};

    for (const file of files) {
        const ext = path.extname(file).toLowerCase();
        let matched = false;

        for (const [lang, exts] of Object.entries(languages)) {
            if (exts.includes(ext)) {
                langCount[lang] = (langCount[lang] || 0) + 1;
                matched = true;
                break;
            }
        }

        if (!matched && ext) {
            langCount.Other = (langCount.Other || 0) + 1;
        }
    }

    return Object.entries(langCount)
        .map(([lang, count]) => ({ lang, count }))
        .sort((a, b) => b.count - a.count);
}


    getFirstCommit() {
        return this.exec('git log --reverse --format="%H|%an|%ae|%ad" --date=short | head -1');
    }

    getLastCommit() {
        return this.exec('git log -1 --format="%H|%an|%ae|%ad" --date=short');
    }

    getCommitActivity() {
        const output = this.exec('git log --format="%ad" --date=short');
        const dates = output.split('\n');
        
        const activity = {};
        dates.forEach(date => {
            if (date) {
                activity[date] = (activity[date] || 0) + 1;
            }
        });
        
        return activity;
    }

    getTags() {
        const output = this.exec('git tag');
        return output ? output.split('\n').filter(t => t) : [];
    }

    getBranches() {
    const output = this.exec('git branch -a');
    if (!output) return 0;

    const branches = new Set();

    output.split('\n').forEach(line => {
        let name = line.trim();

        if (name.startsWith('* ')) {
            name = name.slice(2);
        }

        if (name.includes('HEAD ->')) return;

        branches.add(name);
    });

    return branches.size;
}

    getCodeChurn() {
        const output = this.exec('git log --all --numstat --format="" --no-merges');
        let added = 0;
        let deleted = 0;
        
        output.split('\n').forEach(line => {
            const match = line.match(/^(\d+)\s+(\d+)/);
            if (match) {
                added += parseInt(match[1]);
                deleted += parseInt(match[2]);
            }
        });
        
        return { added, deleted, total: added + deleted };
    }

    getActiveContributors(days = 30) {
        const since = `${days} days ago`;
        const output = this.exec(`git shortlog -sn --since="${since}" --no-merges`);
        if (!output) return 0;
        return output.split('\n').filter(l => l.trim()).length;
    }

    formatNumber(num) {
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    }

    createProgressBar(value, max, width = 30) {
        const percentage = Math.min((value / max) * 100, 100);
        const filled = Math.round((percentage / 100) * width);
        const empty = width - filled;
        return '█'.repeat(filled) + '░'.repeat(empty) + ` ${percentage.toFixed(1)}%`;
    }

    displayStats() {
        if (!this.isGitRepo) {
            console.log('❌ Not a git repository!');
            return;
        }

        const repoName = this.getRepoName();
        const branch = this.getCurrentBranch();
        const totalCommits = this.getTotalCommits();
        const authors = this.getCommitsByAuthor();
        const fileStats = this.getFileStats();
        const languages = this.getLanguageStats();
        const firstCommit = this.getFirstCommit();
        const lastCommit = this.getLastCommit();
        const tags = this.getTags();
        const branches = this.getBranches();
        const churn = this.getCodeChurn();
        const activeContributors = this.getActiveContributors(30);

        console.log('\n╔═══════════════════════════════════════════════════════════════════════╗');
        console.log('║                          Git Repository Stats                        ║');
        console.log('╚═══════════════════════════════════════════════════════════════════════╝\n');

        console.log(`📁 Repository: ${repoName}`);
        console.log(`🌿 Branch:     ${branch}`);
        console.log(`📊 Commits:    ${this.formatNumber(totalCommits)}`);
        console.log(`🏷️  Tags:       ${tags.length}`);
        console.log(`🌳 Branches:   ${branches}`);
        console.log(`👥 Active (30d): ${activeContributors} contributor(s)\n`);

        if (firstCommit) {
            const [hash, name, email, date] = firstCommit.split('|');
            console.log('═══════════════════════════════════════════════════════════════════════');
            console.log('First Commit:');
            console.log('═══════════════════════════════════════════════════════════════════════');
            console.log(`  📅 Date:   ${date}`);
            console.log(`  👤 Author: ${name} <${email}>`);
            console.log(`  🔑 Hash:   ${hash.substring(0, 12)}\n`);
        }

        if (lastCommit) {
            const [hash, name, email, date] = lastCommit.split('|');
            console.log('═══════════════════════════════════════════════════════════════════════');
            console.log('Latest Commit:');
            console.log('═══════════════════════════════════════════════════════════════════════');
            console.log(`  📅 Date:   ${date}`);
            console.log(`  👤 Author: ${name} <${email}>`);
            console.log(`  🔑 Hash:   ${hash.substring(0, 12)}\n`);
        }

        console.log('═══════════════════════════════════════════════════════════════════════');
        console.log('Top Contributors:');
        console.log('═══════════════════════════════════════════════════════════════════════');
        const topAuthors = authors.slice(0, 10);
        const maxCommits = topAuthors[0]?.commits || 1;
        
        topAuthors.forEach((author, idx) => {
            const bar = this.createProgressBar(author.commits, maxCommits, 25);
            console.log(`  ${(idx + 1).toString().padStart(2)}. ${author.name.padEnd(25)} ${this.formatNumber(author.commits).padStart(6)} ${bar}`);
        });
        console.log();

        console.log('═══════════════════════════════════════════════════════════════════════');
        console.log('Languages:');
        console.log('═══════════════════════════════════════════════════════════════════════');
        if (languages.length === 0) {
            console.log('  No language files detected');
        } else {
            const topLangs = languages.slice(0, 10);
            const maxFiles = topLangs[0]?.count || 1;
            
            topLangs.forEach(lang => {
                const bar = this.createProgressBar(lang.count, maxFiles, 25);
                console.log(`  ${lang.lang.padEnd(15)} ${lang.count.toString().padStart(6)} files ${bar}`);
            });
        }
        console.log();

        console.log('═══════════════════════════════════════════════════════════════════════');
        console.log('Code Statistics:');
        console.log('═══════════════════════════════════════════════════════════════════════');
        console.log(`  Total Files:       ${this.formatNumber(fileStats.total)}`);
        console.log(`  Lines Added:       ${this.formatNumber(churn.added)}`);
        console.log(`  Lines Deleted:     ${this.formatNumber(churn.deleted)}`);
        console.log(`  Total Changes:     ${this.formatNumber(churn.total)}\n`);

        console.log('═══════════════════════════════════════════════════════════════════════');
        console.log('File Extensions:');
        console.log('═══════════════════════════════════════════════════════════════════════');
        if (fileStats.extensions.length === 0) {
            console.log('  No files detected');
        } else {
            const topExts = fileStats.extensions.slice(0, 15);
            const maxExtCount = topExts[0]?.count || 1;
            
            topExts.forEach(ext => {
                const bar = this.createProgressBar(ext.count, maxExtCount, 25);
                console.log(`  ${ext.ext.padEnd(20)} ${ext.count.toString().padStart(6)} ${bar}`);
            });
        }
        console.log();
    }
}

const args = process.argv.slice(2);
const repoPath = args[0] || '.';

const stats = new GitStats(repoPath);
stats.displayStats();
